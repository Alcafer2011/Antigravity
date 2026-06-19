const sharp = require('sharp');
const fs = require('fs');

// Read SVG file
const svgBuffer = fs.readFileSync('./icon.svg');

// Convert SVG to PNG
sharp(svgBuffer)
  .png()
  .toFile('./icon.png')
  .then(() => console.log('Icon converted successfully!'))
  .catch(err => console.error('Error converting icon:', err));
