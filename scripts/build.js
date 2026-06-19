const esbuild = require('esbuild');
const path = require('path');

const isProduction = process.argv.includes('--production');

const context = {
    entryPoints: ['extension.js'],
    bundle: true,
    platform: 'node',
    target: 'node16',
    external: ['vscode', 'sharp'],
    outfile: path.join(__dirname, '..', 'build', 'extension.js'),
    minify: isProduction,
    sourcemap: !isProduction,
    logLevel: 'info',
};

async function build() {
    try {
        await esbuild.build(context);
        console.log('Build completed successfully!');
    } catch (error) {
        console.error('Build failed:', error);
        process.exit(1);
    }
}

build();
