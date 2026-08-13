'use client';

import { forwardRef, useImperativeHandle, useRef } from 'react';
import { OrbitControls, View as ViewImpl } from '@react-three/drei';
import { Three } from '@/webgl/helpers/Three';

const View = forwardRef(({ children, orbit, ...props }, ref) => {
    const localRef = useRef(null);
    useImperativeHandle(ref, () => localRef.current);

    return (
        <>
            <div ref={localRef} {...props} />
            <Three>
                <ViewImpl track={localRef}>
                    {children}
                    {orbit && <OrbitControls />}
                </ViewImpl>
            </Three>
        </>
    );
});

View.displayName = 'View';

export { View };
