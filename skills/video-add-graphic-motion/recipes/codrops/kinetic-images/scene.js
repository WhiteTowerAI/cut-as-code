/*
 * HyperFrames port of DGFX/codrops-kinetic-images at
 * 965dda362a8f9e5d522ed675493897200d273e49.
 * Source: https://github.com/DGFX/codrops-kinetic-images
 * License: MIT, https://tympanus.net/codrops/licensing/
 */
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { sceneStateAt, showcaseStateAt } from "./scene-time.js";

const IMAGE_URLS = Array.from(
  { length: 13 },
  (_, index) => new URL(`./upstream/public/images/img${index + 1}.webp`, import.meta.url).href,
);

class MeshImageMaterial extends THREE.MeshBasicMaterial {
  onBeforeCompile(shader) {
    shader.fragmentShader = shader.fragmentShader.replace(
      "#include <color_fragment>",
      `#include <color_fragment>
       if (!gl_FrontFacing) diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.0), 0.7);`,
    );
  }
}

class MeshBannerMaterial extends THREE.MeshBasicMaterial {
  onBeforeCompile(shader) {
    shader.uniforms.repeatX = { value: 0.2 };
    shader.fragmentShader = shader.fragmentShader
      .replace(
        "#include <common>",
        `#include <common>
         uniform float repeatX;
         vec3 hfPalette(float t, vec3 a, vec3 b, vec3 c, vec3 d) {
           return a + b * cos(6.28318 * (c * t + d));
         }`,
      )
      .replace(
        "#include <color_fragment>",
        `#include <color_fragment>
         if (!gl_FrontFacing) {
           diffuseColor.rgb = hfPalette(vMapUv.x * repeatX, vec3(0.5), vec3(0.5), vec3(1.0), vec3(0.0, 0.10, 0.20));
         }`,
      );
  }
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Failed to load image: ${url}`));
    image.src = url;
  });
}

async function collageTexture(urls, { axis = "x", canvasHeight = 512, canvasWidth = 512 } = {}) {
  const images = await Promise.all(urls.map(loadImage));
  const sizes = images.map((image) => {
    const aspect = image.naturalWidth / image.naturalHeight;
    return axis === "x"
      ? { width: canvasHeight * aspect, height: canvasHeight }
      : { width: canvasWidth, height: canvasWidth / aspect };
  });
  const width = axis === "x" ? sizes.reduce((sum, item) => sum + item.width, 0) : canvasWidth;
  const height = axis === "y" ? sizes.reduce((sum, item) => sum + item.height, 0) : canvasHeight;
  const canvas = document.createElement("canvas");
  canvas.width = Math.ceil(width);
  canvas.height = Math.ceil(height);
  const context = canvas.getContext("2d");
  context.fillStyle = "#fff";
  context.fillRect(0, 0, width, height);
  let cursor = 0;
  images.forEach((image, index) => {
    const size = sizes[index];
    context.drawImage(image, axis === "x" ? cursor : 0, axis === "y" ? cursor : 0, size.width, size.height);
    cursor += axis === "x" ? size.width : size.height;
  });
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.generateMipmaps = false;
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  return { texture, aspect: width / height };
}

function makeCylinders(billboardTexture, billboardAspect, bannerTexture) {
  const group = new THREE.Group();
  group.rotation.set(-0.15, 0, -0.2);
  const radius = 5;
  const gap = 3.2;
  const billboardGeometry = new THREE.CylinderGeometry(radius, radius, 2, 100, 1, true);
  const circumferenceAspect = (2 * Math.PI * radius) / 2;
  billboardTexture.repeat.x = Math.min(1, circumferenceAspect / billboardAspect);
  billboardTexture.repeat.y = Math.min(1, billboardAspect / circumferenceAspect);
  billboardTexture.offset.set((1 - billboardTexture.repeat.x) / 2, (1 - billboardTexture.repeat.y) / 2);
  const billboardMaterial = new MeshImageMaterial({ map: billboardTexture, side: THREE.DoubleSide, toneMapped: false });
  bannerTexture.wrapS = bannerTexture.wrapT = THREE.RepeatWrapping;
  bannerTexture.repeat.set(15, 1);
  const bannerMaterial = new MeshBannerMaterial({ map: bannerTexture, side: THREE.DoubleSide, toneMapped: false });
  const bannerGeometry = new THREE.CylinderGeometry(5.035, 5.035, 5.035 * 0.07, 400, 50, true);

  for (let index = 0; index < 10; index += 1) {
    const y = (index - 4) * gap;
    const billboard = new THREE.Mesh(billboardGeometry, billboardMaterial);
    billboard.rotation.y = index * Math.PI * 0.5;
    billboard.position.y = y;
    group.add(billboard);
    const banner = new THREE.Mesh(bannerGeometry, bannerMaterial);
    banner.rotation.z = 0.085;
    banner.position.y = y - gap * 0.5;
    group.add(banner);
  }
  return { group, billboardTexture, bannerTexture };
}

async function makeModel(url, texture, materialFactory, transform) {
  const gltf = await new GLTFLoader().loadAsync(url);
  const object = gltf.scene;
  const mesh = object.children[0];
  mesh.material = materialFactory(texture, mesh.material);
  transform(object);
  return object;
}

export async function createRecipe({ canvas }) {
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(1920, 1080, false);
  renderer.setPixelRatio(1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setClearColor(0x000000, 0);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(7, 1920 / 1080, 0.01, 100000);

  const [{ texture: billboardTexture, aspect }, { texture: paperTexture }, bannerTexture] = await Promise.all([
    collageTexture(IMAGE_URLS),
    collageTexture(IMAGE_URLS.slice(0, 5), { axis: "y", canvasWidth: 1024 }),
    new THREE.TextureLoader().loadAsync(new URL("./upstream/public/banner.jpg", import.meta.url).href),
  ]);
  bannerTexture.colorSpace = THREE.SRGBColorSpace;
  const cylinders = makeCylinders(billboardTexture, aspect, bannerTexture);
  scene.add(cylinders.group);

  const paper = await makeModel(
    new URL("./upstream/public/paper.glb", import.meta.url).href,
    paperTexture,
    (texture, material) => {
      material.map = texture;
      material.toneMapped = false;
      material.needsUpdate = true;
      return material;
    },
    (object) => {
      object.rotation.y = Math.PI * 0.3;
      object.position.y = 0.5;
    },
  );
  scene.add(paper);

  const { texture: spiralTexture } = await collageTexture(IMAGE_URLS);
  const spiral = await makeModel(
    new URL("./upstream/public/spiral.glb", import.meta.url).href,
    spiralTexture,
    (texture) => new MeshImageMaterial({ map: texture, side: THREE.DoubleSide, toneMapped: false }),
    () => {},
  );
  scene.add(spiral);

  function renderAt(time) {
    const requestedMode = canvas.dataset.sceneMode || "showcase";
    const showcase = requestedMode === "showcase" ? showcaseStateAt(time) : null;
    const mode = showcase?.mode || requestedMode;
    const localTime = showcase?.localTime ?? Math.max(0, time);
    cylinders.group.visible = mode === "cylinders";
    paper.visible = mode === "paper";
    spiral.visible = mode === "spiral";

    if (mode === "cylinders") {
      Object.assign(camera, { fov: 7 });
      camera.position.set(0, 0, 70);
      const state = sceneStateAt(mode, localTime);
      cylinders.billboardTexture.offset.x = state.billboardOffsetX;
      cylinders.bannerTexture.offset.x = state.bannerOffsetX;
    } else if (mode === "paper") {
      Object.assign(camera, { fov: 20 });
      camera.position.set(0, 0, 13);
      paperTexture.offset.y = sceneStateAt(mode, localTime).textureOffsetY;
    } else if (mode === "spiral") {
      Object.assign(camera, { fov: 7 });
      camera.position.set(0, 0, 100);
      spiralTexture.offset.x = sceneStateAt(mode, localTime).textureOffsetX;
    } else {
      throw new Error(`unsupported kinetic-images mode: ${mode}`);
    }
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
  }

  return { renderAt };
}
