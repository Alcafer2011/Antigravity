const esbuild = require('esbuild');
const path = require('path');

const context = {
    entryPoints: ['extension.js'],
    bundle: true,
    platform: 'node',
    target: 'node16',
    external: ['vscode', 'sharp'],
    outfile: path.join(__dirname, '..', 'build', 'extension.js'),
    minify: false,
    sourcemap: true,
    logLevel: 'info',
    watch: {
        onRebuild: (error, result) => {
            if (error) console.error('Watch build failed:', error);
            else console.log('Watch build succeeded!');
        },
    },
};

async function watch() {
    try {
        const ctx = await esbuild.context(context);
        await ctx.watch();
        console.log('Watching for changes...');
    } catch (error) {
        console.error('Watch failed:', error);
        process.exit(1);
    }
}

watch();
