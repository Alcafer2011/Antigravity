const sharp = require('sharp');
const fs = require('fs');

// GitHub icon guidelines: square icons (1:1 aspect ratio)
// Required sizes: 16x16, 32x32, 48x48, 128x128, 256x256
const sizes = [16, 32, 48, 128, 256];

async function generateIcons() {
    const svgBuffer = fs.readFileSync('icon.svg');
    
    for (const size of sizes) {
        try {
            await sharp(svgBuffer)
                .resize(size, size)
                .png()
                .toFile(`icon-${size}x${size}.png`);
            console.log(`Generated icon-${size}x${size}.png`);
        } catch (error) {
            console.error(`Error generating ${size}x${size}:`, error);
        }
    }
    
    // Also generate the default icon.png (128x128)
    await sharp(svgBuffer)
        .resize(128, 128)
        .png()
        .toFile('icon.png');
    console.log('Generated icon.png (128x128)');
}

generateIcons().catch(console.error);
