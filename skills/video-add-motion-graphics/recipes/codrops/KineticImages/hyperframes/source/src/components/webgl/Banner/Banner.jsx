'use client';

import * as THREE from 'three';
import { useTexture } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';

import '@/webgl/materials/MeshBannerMaterial';

function Banner({ radius = 1.6, ...props }) {
    const ref = useRef(null);

    const texture = useTexture('/banner.jpg');
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;

    useFrame((state, delta) => {
        if (!ref.current) return;
        const material = ref.current.material;
        if (material.map) material.map.offset.x += delta / 30;
    });

    return (
        <mesh ref={ref} {...props}>
            <cylinderGeometry
                args={[radius, radius, radius * 0.07, radius * 80, radius * 10, true]}
            />
            <meshBannerMaterial
                map={texture}
                map-anisotropy={16}
                map-repeat={[15, 1]}
                side={THREE.DoubleSide}
                toneMapped={false}
                backfaceRepeatX={0.2}
            />
        </mesh>
    );
}

export default Banner;
