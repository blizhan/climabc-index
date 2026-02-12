import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'
import { execFileSync } from 'child_process'

function resolveDataPath(defaultRelativePath: string, envKeys: string[]): string {
  for (const envKey of envKeys) {
    const envValue = process.env[envKey]
    if (envValue && envValue.trim().length > 0) {
      return path.resolve(__dirname, '..', envValue)
    }
  }
  return path.resolve(__dirname, '..', defaultRelativePath)
}

function loadParquetDataset(observationPath: string, forecastPath: string): string {
  const scriptPath = path.resolve(__dirname, 'scripts/parquet_to_frontend_json.py')
  const pythonCandidates = Array.from(new Set([
    process.env.CLIMABC_PYTHON_BIN || '',
    path.resolve(__dirname, '..', '.venv', 'bin', 'python'),
    'python3',
    'python',
  ].filter(Boolean)))

  let lastError: unknown
  for (const pythonBin of pythonCandidates) {
    if (pythonBin.includes(path.sep) && !fs.existsSync(pythonBin)) {
      continue
    }
    try {
      return execFileSync(pythonBin, [scriptPath, observationPath, forecastPath], {
        encoding: 'utf-8',
      })
    } catch (error) {
      lastError = error
    }
  }

  throw lastError
}

function isPathInside(rootDir: string, targetPath: string): boolean {
  const normalizedRoot = path.resolve(rootDir)
  const normalizedTarget = path.resolve(targetPath)
  return (
    normalizedTarget === normalizedRoot ||
    normalizedTarget.startsWith(`${normalizedRoot}${path.sep}`)
  )
}

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'climabc-parquet-api',
      configureServer(server) {
        const dataRoot = path.resolve(__dirname, '..', 'data')

        server.middlewares.use('/data', (req, res, next) => {
          const requestPath = decodeURIComponent((req.url || '').split('?')[0] || '/')
          const relativePath = requestPath.replace(/^\/+/, '')
          const filePath = path.resolve(dataRoot, relativePath)

          if (!isPathInside(dataRoot, filePath)) {
            res.statusCode = 403
            res.end('Forbidden')
            return
          }
          if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
            next()
            return
          }

          if (filePath.endsWith('.parquet')) {
            res.setHeader('Content-Type', 'application/octet-stream')
          }
          fs.createReadStream(filePath).pipe(res)
        })

        server.middlewares.use('/api/enso-data', (_req, res) => {
          const observationPath = resolveDataPath('data/observations', ['CLIMABC_OBSERVATIONS_PATH', 'CLIMABC_OBS_PARQUET'])
          const forecastPath = resolveDataPath('data/forecasts', ['CLIMABC_FORECASTS_PATH', 'CLIMABC_FORECAST_PARQUET'])

          if (!fs.existsSync(observationPath)) {
            res.statusCode = 404
            res.setHeader('Content-Type', 'application/json; charset=utf-8')
            res.end(JSON.stringify({ error: `Observations path not found: ${observationPath}` }))
            return
          }
          if (!fs.existsSync(forecastPath)) {
            res.statusCode = 404
            res.setHeader('Content-Type', 'application/json; charset=utf-8')
            res.end(JSON.stringify({ error: `Forecasts path not found: ${forecastPath}` }))
            return
          }

          try {
            const payload = loadParquetDataset(observationPath, forecastPath)
            res.statusCode = 200
            res.setHeader('Content-Type', 'application/json; charset=utf-8')
            res.end(payload)
          } catch (error) {
            const message = error instanceof Error ? error.message : String(error)
            res.statusCode = 500
            res.setHeader('Content-Type', 'application/json; charset=utf-8')
            res.end(JSON.stringify({ error: `Failed to load parquet dataset: ${message}` }))
          }
        })
      },
    },
  ],
  base: './',
  build: {
    outDir: 'dist',
    sourcemap: true
  },
  publicDir: 'public',
  server: {
    fs: {
      allow: [
        path.resolve(__dirname, '.'),
        path.resolve(__dirname, '../data')
      ]
    }
  }
})
