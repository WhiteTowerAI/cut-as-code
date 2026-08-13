'use client';

import { Canvas } from '@react-three/fiber';
import { Preload } from '@react-three/drei';
import { r3f } from '@/webgl/helpers/global';
import * as THREE from 'three';

export default function Scene(props) {
    return (
        <Canvas {...props}>
            <r3f.Out />
            <Preload all />
        </Canvas>
    );
}
