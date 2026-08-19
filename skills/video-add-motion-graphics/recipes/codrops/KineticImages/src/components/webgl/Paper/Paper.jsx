'use client';

import * as THREE from 'three';
import { useGLTF } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useEffect } from 'react';

function setupPaperMaterial(texture, material) {
    material.map = texture;
    material.toneMapped = false;
}

function Paper({ texture, ...props }) {
    const { scene } = useGLTF('/paper.glb');

    const mesh = scene.children[0];

    useEffect(() => {
        if (!texture) return;
        texture.colorSpace = THREE.SRGBColorSpace;
        setupPaperMaterial(texture, mesh.material);
    }, [texture, mesh.material]);

    useFrame((state, delta) => {
        if (!texture) return;
        texture.offset.y += delta / 30;
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
    });

    return <primitive {...props} object={scene} />;
}

export default Paper;
