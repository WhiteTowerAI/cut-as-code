'use client';

import * as THREE from 'three';
import { useEffect } from 'react';
import { useGLTF } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { MeshImageMaterial } from '@/webgl/materials/MeshImageMaterial';

function setupSpiralMaterial(texture, mesh) {
    mesh.material = new MeshImageMaterial({
        map: texture,
        side: THREE.DoubleSide,
        toneMapped: false,
    });
}

function Spiral({ texture }) {
    const { scene } = useGLTF('/spiral.glb');
    const mesh = scene.children[0];

    useEffect(() => {
        if (!texture) return;
        texture.colorSpace = THREE.SRGBColorSpace;
        setupSpiralMaterial(texture, mesh);
    }, [texture, mesh]);

    useFrame((state, delta) => {
        const material = mesh.material;

        if (!material || !material.map) return;
        material.map.offset.x -= delta / 50;
        material.map.wrapS = THREE.RepeatWrapping;
        material.map.wrapT = THREE.RepeatWrapping;
    });

    return <primitive object={scene} />;
}

export default Spiral;
