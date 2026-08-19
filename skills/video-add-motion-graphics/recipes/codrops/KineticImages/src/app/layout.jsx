import '@/styles/global.scss';

import { Suspense } from 'react';
import meta from '@/data/metadata';
import fontFaces from '@/assets/fonts/font-faces';
import { Layout } from '@/components/layouts/Layout';

export const metadata = meta;

export default function RootLayout({ children }) {
    return (
        <html lang="en">
            <body className={`${fontFaces}`}>
                <Suspense>
                    <Layout>{children}</Layout>
                </Suspense>
            </body>
        </html>
    );
}
