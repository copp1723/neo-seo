// server.js

console.log('Starting server.js...');

const express = require('express');
const multer = require('multer');
const { spawn } = require('child_process');
const path = require('path');

// Create an Express app
const app = express();

// Multer setup: files go into a folder named "uploads"
const upload = multer({ dest: 'uploads/' });

// Serve a simple HTML form at the root path
app.get('/', (req, res) => {
  res.send(`
    <h1>Neosemo CSV Processor</h1>
    <form action="/upload" method="POST" enctype="multipart/form-data">
      <input type="file" name="csvFile" accept=".csv" />
      <button type="submit">Upload & Process</button>
    </form>
  `);
});

// Handle the CSV upload and run the Python script
app.post('/upload', upload.single('csvFile'), (req, res) => {
  // The path to the uploaded file on the server
  const inputFile = req.file.path;

  // Where we want to save the processed CSV
  const outputFile = path.join(__dirname, 'uploads', 'processed.csv');

  // Path to your Python script (same folder as server.js)
  const pythonScriptPath = path.join(__dirname, 'run_dealerships.py');

  // Spawn the Python process with the input and output file paths
  const process = spawn('python3', [
    pythonScriptPath,
    inputFile,
    outputFile
  ]);

  // Optional: log Python script output
  process.stdout.on('data', (data) => {
    console.log(`Python STDOUT: ${data}`);
  });

  // Optional: log Python script errors
  process.stderr.on('data', (data) => {
    console.error(`Python STDERR: ${data}`);
  });

  // When the Python script finishes...
  process.on('close', (code) => {
    console.log(`Python script exited with code ${code}`);
    if (code === 0) {
      // Send the processed file back to the user for download
      res.download(outputFile, 'processed.csv', (err) => {
        if (err) {
          console.error('Error sending file:', err);
          res.status(500).send('Error downloading processed file.');
        }
      });
    } else {
      res.status(500).send('Python script failed.');
    }
  });
});

// Start the server
const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
