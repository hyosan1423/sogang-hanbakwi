import { build } from 'esbuild';
await build({
  entryPoints: ['src/fb.js'], bundle: true, minify: true, format: 'iife', target: ['es2019'],
  outfile: 'public/assets/fb.js', legalComments: 'none'
});
console.log('fb.js bundled');
