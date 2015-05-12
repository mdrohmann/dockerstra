var gulp = require('gulp');
var browserSync = require('browser-sync').create();
var shelljs = require('shelljs');

gulp.task('serve', ['sphinx'], function() {
    browserSync.init({
        server: {
            baseDir: '.build/html'
        }
    });

    gulp.watch('./**/*.rst', ['sphinx']);
});

gulp.task('sphinx', [], function() {

    shelljs.exec('make html', function(code, output) {
        console.log('Exit code:', code);
        console.log('Program output:', output);
        browserSync.reload();
    });
});

/* vim:set et sw=4 ts=8: */
