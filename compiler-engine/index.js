const express = require('express');
const { exec, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const app = express();
app.use(express.json({ limit: '10mb' }));

const PORT = process.env.PORT || 8000;
const TEMP_DIR = path.join(__dirname, 'temp');

if (!fs.existsSync(TEMP_DIR)) {
  fs.mkdirSync(TEMP_DIR, { recursive: true });
}

const ALLOWED_LANGUAGES = ['cpp', 'py', 'java'];

app.post('/run', (req, res) => {
  const { language, code, input } = req.body;

  if (!code || typeof code !== 'string') {
    return res.status(400).json({ output: '', error: 'No code provided.' });
  }

  const lang = (language || '').toLowerCase().trim();
  if (!ALLOWED_LANGUAGES.includes(lang)) {
    return res.status(400).json({ output: '', error: `Unsupported language. Allowed: ${ALLOWED_LANGUAGES.join(', ')}` });
  }

  const jobFolder = path.join(TEMP_DIR, crypto.randomBytes(8).toString('hex'));
  fs.mkdirSync(jobFolder, { recursive: true });

  const inputPath = path.join(jobFolder, 'input.txt');
  fs.writeFileSync(inputPath, input || '');

  let fileExt = 'cpp';
  if (lang === 'py') fileExt = 'py';
  else if (lang === 'java') fileExt = 'java';

  const codePath = path.join(jobFolder, lang === 'java' ? 'Main.java' : `solution.${fileExt}`);
  fs.writeFileSync(codePath, code);

  let runCmd = '';
  if (lang === 'cpp') {
    const outPath = path.join(jobFolder, 'solution.out');
    runCmd = `g++ "${codePath}" -o "${outPath}" && "${outPath}" < "${inputPath}"`;
  } else if (lang === 'py') {
    runCmd = `python3 "${codePath}" < "${inputPath}"`;
  } else if (lang === 'java') {
    runCmd = `javac "${codePath}" && java -cp "${jobFolder}" Main < "${inputPath}"`;
  }

  exec(runCmd, { timeout: 10000, maxBuffer: 1024 * 1024 * 5, killSignal: 'SIGKILL' }, (err, stdout, stderr) => {
    // Cleanup temporary directory
    fs.rm(jobFolder, { recursive: true, force: true }, () => {});

    if (err) {
      return res.json({
        output: stdout ? stdout.toString() : '',
        error: stderr ? stderr.toString() : err.message
      });
    }

    return res.json({
      output: stdout ? stdout.toString() : '',
      error: stderr ? stderr.toString() : ''
    });
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.listen(PORT, () => {
  console.log(`Compiler engine microservice listening on port ${PORT}`);
});
