const sharp = require('sharp');
const fs = require('fs');

// Read and resize icon to 128x128
sharp('./icon.svg')
  .resize(128, 128)
  .png()
  .toFile('./icon.png')
  .then(() => console.log('Icon resized to 128x128 successfully!'))
  .catch(err => console.error('Error resizing icon:', err));
