const express = require('express');
const cors = require('cors');
const axios = require('axios');
require('dotenv').config();

const app = express();
const port = process.env.PORT || 4010;
const githubOwner = process.env.GITHUB_OWNER || 'SteadEvent7';
const githubRepo = process.env.GITHUB_REPO || 'pharmadesk';
const githubToken = process.env.GITHUB_TOKEN || '';
const publicBaseUrl = (process.env.PUBLIC_BASE_URL || `http://127.0.0.1:${port}`).replace(/\/$/, '');
const releaseAssetName = process.env.RELEASE_ASSET_NAME || 'PharmaDeskSetup.exe';
const releaseAssetExtension = process.env.RELEASE_ASSET_EXTENSION || '.exe';
const releasePatch = Number.parseInt(process.env.RELEASE_PATCH || '0', 10) || 0;
const proxyDownloads = String(process.env.DOWNLOAD_VIA_SERVICE || 'true').toLowerCase() !== 'false';

app.use(cors());
app.use(express.json());

function githubHeaders() {
  const headers = {
    Accept: 'application/vnd.github+json',
    'User-Agent': 'pharmadesk-updater-service'
  };
  if (githubToken) {
    headers.Authorization = `Bearer ${githubToken}`;
  }
  return headers;
}

function normalizeVersion(tagName) {
  return String(tagName || '').replace(/^v/i, '').trim();
}

function pickInstallerAsset(release) {
  const assets = Array.isArray(release.assets) ? release.assets : [];
  const exactMatch = assets.find((asset) => asset.name === releaseAssetName);
  if (exactMatch) {
    return exactMatch;
  }

  const fallbackMatch = assets.find((asset) => asset.name.toLowerCase().endsWith(releaseAssetExtension.toLowerCase()));
  return fallbackMatch || null;
}

function releaseToManifest(release) {
  const installerAsset = pickInstallerAsset(release);
  if (!installerAsset) {
    return null;
  }

  const directDownloadUrl = installerAsset.browser_download_url;
  const proxiedDownloadUrl = `${publicBaseUrl}/download?assetUrl=${encodeURIComponent(directDownloadUrl)}`;
  return {
    version: normalizeVersion(release.tag_name),
    patch: releasePatch,
    published_at: release.published_at || '',
    installer_name: installerAsset.name,
    installer_url: proxyDownloads ? proxiedDownloadUrl : directDownloadUrl,
    notes: release.body || '',
    sha256: '',
    source: {
      repository: `${githubOwner}/${githubRepo}`,
      tag: String(release.tag_name || ''),
      asset: installerAsset.name,
      proxied_download: proxyDownloads
    }
  };
}

async function getLatestRelease() {
  const response = await axios.get(
    `https://api.github.com/repos/${githubOwner}/${githubRepo}/releases/latest`,
    { headers: githubHeaders() }
  );
  return response.data;
}

app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

app.get('/latest', async (_req, res) => {
  try {
    const release = await getLatestRelease();
    res.json({
      version: normalizeVersion(release.tag_name),
      publishedAt: release.published_at,
      notes: release.body || '',
      assets: (release.assets || []).map((asset) => ({
        name: asset.name,
        size: asset.size,
        downloadUrl: asset.browser_download_url
      }))
    });
  } catch (error) {
    res.status(502).json({ message: 'Impossible de recuperer la derniere release GitHub.' });
  }
});

app.get('/manifest', async (_req, res) => {
  try {
    const release = await getLatestRelease();
    const manifest = releaseToManifest(release);
    if (!manifest) {
      return res.status(404).json({
        message: `Aucun asset installateur compatible n'a ete trouve. Asset attendu: ${releaseAssetName} ou extension ${releaseAssetExtension}`
      });
    }
    return res.json(manifest);
  } catch (error) {
    return res.status(502).json({ message: 'Impossible de generer le manifest de mise a jour.' });
  }
});

app.get('/download', async (req, res) => {
  const { assetUrl } = req.query;
  if (!assetUrl) {
    return res.status(400).json({ message: 'Le parametre assetUrl est requis.' });
  }

  try {
    const response = await axios.get(assetUrl, {
      responseType: 'stream',
      headers: githubHeaders()
    });
    res.setHeader('Content-Disposition', response.headers['content-disposition'] || 'attachment');
    response.data.pipe(res);
  } catch (error) {
    res.status(502).json({ message: 'Telechargement impossible.' });
  }
});

app.listen(port, () => {
  console.log(`Updater service listening on port ${port}`);
  console.log(`Manifest endpoint: ${publicBaseUrl}/manifest`);
});