import { Geist } from 'next/font/google';

const geist = Geist({
    subsets: ['latin'],
});

const fonts = [geist];

function getFontFaces() {
    let fontFaces = '';
    fonts.forEach((font) => {
        fontFaces += `${font.className} `;
    });

    return fontFaces;
}

const fontFaces = getFontFaces();

export default fontFaces;
