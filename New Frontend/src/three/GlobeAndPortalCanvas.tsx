import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

interface GlobeAndPortalCanvasProps {
  mode: 'analyzing' | 'searching' | 'portal';
  progress?: number;
  reducedMotion?: boolean;
}

export const GlobeAndPortalCanvas: React.FC<GlobeAndPortalCanvasProps> = ({
  mode,
  progress = 0,
  reducedMotion = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [webglSupported, setWebglSupported] = useState(true);

  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    // Check WebGL availability
    try {
      const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
      if (!gl) {
        setWebglSupported(false);
        return;
      }
    } catch {
      setWebglSupported(false);
      return;
    }

    // Set up Three.js Scene
    const scene = new THREE.Scene();

    const width = container.clientWidth || 480;
    const height = container.clientHeight || 480;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.z = 4.2;

    const renderer = new THREE.WebGLRenderer({
      canvas,
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Studio Lights
    const ambientLight = new THREE.AmbientLight(0x38bdf8, 0.6);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0x6366f1, 2.5);
    keyLight.position.set(3, 4, 3);
    scene.add(keyLight);

    const rimLight = new THREE.PointLight(0xa855f7, 3, 10);
    rimLight.position.set(-3, -2, -2);
    scene.add(rimLight);

    const group = new THREE.Group();
    scene.add(group);

    // 1. Particle Globe
    const particleCount = 750;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    const particleColors = new Float32Array(particleCount * 3);
    const globeRadius = 1.6;

    // Colors: cyan, electric blue, violet, accent amber
    const colorChoices = [
      new THREE.Color(0x38bdf8), // cyan
      new THREE.Color(0x6366f1), // indigo
      new THREE.Color(0x818cf8), // blue-purple
      new THREE.Color(0xa855f7), // violet
      new THREE.Color(0xf59e0b), // amber
    ];

    for (let i = 0; i < particleCount; i++) {
      // Golden spiral distribution on sphere
      const phi = Math.acos(1 - 2 * (i + 0.5) / particleCount);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;

      const x = globeRadius * Math.sin(phi) * Math.cos(theta);
      const y = globeRadius * Math.sin(phi) * Math.sin(theta);
      const z = globeRadius * Math.cos(phi);

      particlePositions[i * 3] = x;
      particlePositions[i * 3 + 1] = y;
      particlePositions[i * 3 + 2] = z;

      const chosenColor = colorChoices[i % colorChoices.length];
      particleColors[i * 3] = chosenColor.r;
      particleColors[i * 3 + 1] = chosenColor.g;
      particleColors[i * 3 + 2] = chosenColor.b;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    particleGeo.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

    // Custom circular soft particle texture
    const createCircleTexture = () => {
      const pCanvas = document.createElement('canvas');
      pCanvas.width = 32;
      pCanvas.height = 32;
      const ctx = pCanvas.getContext('2d');
      if (ctx) {
        const gradient = ctx.createRadialGradient(16, 16, 0, 16, 16, 16);
        gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
        gradient.addColorStop(0.3, 'rgba(224, 231, 255, 0.85)');
        gradient.addColorStop(0.7, 'rgba(99, 102, 241, 0.3)');
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 32, 32);
      }
      return new THREE.CanvasTexture(pCanvas);
    };

    const particleTexture = createCircleTexture();

    const particleMat = new THREE.PointsMaterial({
      size: 0.065,
      map: particleTexture,
      transparent: true,
      vertexColors: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const globePoints = new THREE.Points(particleGeo, particleMat);
    group.add(globePoints);

    // 2. Subtle latitude / longitude orbit rings
    const ringMat = new THREE.LineBasicMaterial({
      color: 0x4f46e5,
      transparent: true,
      opacity: 0.22,
    });

    const ringCount = 3;
    for (let r = 0; r < ringCount; r++) {
      const ringRadius = globeRadius * (0.6 + r * 0.2);
      const ringGeo = new THREE.BufferGeometry();
      const points: THREE.Vector3[] = [];
      const segments = 64;
      for (let s = 0; s <= segments; s++) {
        const angle = (s / segments) * Math.PI * 2;
        points.push(new THREE.Vector3(Math.cos(angle) * ringRadius, 0, Math.sin(angle) * ringRadius));
      }
      ringGeo.setFromPoints(points);
      const ring = new THREE.Line(ringGeo, ringMat);
      ring.rotation.x = (r * 0.4) + 0.3;
      ring.rotation.z = (r * 0.5) - 0.2;
      group.add(ring);
    }

    // 3. Floating 3D Resume Mesh inside the Globe
    const resumeGroup = new THREE.Group();
    // Document body
    const docWidth = 0.7;
    const docHeight = 0.95;
    const docGeo = new THREE.BoxGeometry(docWidth, docHeight, 0.02);
    const docMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.3,
      metalness: 0.6,
      transparent: true,
      opacity: 0.88,
    });
    const docMesh = new THREE.Mesh(docGeo, docMat);
    resumeGroup.add(docMesh);

    // Document border edge glow
    const edgeGeo = new THREE.EdgesGeometry(docGeo);
    const edgeMat = new THREE.LineBasicMaterial({
      color: 0x60a5fa,
      transparent: true,
      opacity: 0.7,
    });
    const edgeLines = new THREE.LineSegments(edgeGeo, edgeMat);
    resumeGroup.add(edgeLines);

    // Abstract text lines on the resume (never personal info)
    const lineMat = new THREE.MeshBasicMaterial({ color: 0x93c5fd, transparent: true, opacity: 0.85 });
    const accentLineMat = new THREE.MeshBasicMaterial({ color: 0x818cf8, transparent: true, opacity: 0.95 });

    // Header bar
    const headerGeo = new THREE.PlaneGeometry(0.5, 0.05);
    const headerMesh = new THREE.Mesh(headerGeo, accentLineMat);
    headerMesh.position.set(0, 0.32, 0.012);
    resumeGroup.add(headerMesh);

    // Subtitle bar
    const subGeo = new THREE.PlaneGeometry(0.35, 0.025);
    const subMesh = new THREE.Mesh(subGeo, lineMat);
    subMesh.position.set(-0.07, 0.24, 0.012);
    resumeGroup.add(subMesh);

    // Content lines
    const lineYPositions = [0.12, 0.05, -0.02, -0.11, -0.18, -0.25, -0.32];
    lineYPositions.forEach((y, idx) => {
      const lineWidth = idx % 2 === 0 ? 0.52 : 0.42;
      const lGeo = new THREE.PlaneGeometry(lineWidth, 0.02);
      const lMesh = new THREE.Mesh(lGeo, idx === 3 ? accentLineMat : lineMat);
      lMesh.position.set((lineWidth - 0.52) / 2, y, 0.012);
      resumeGroup.add(lMesh);
    });

    group.add(resumeGroup);

    // 4. Portal Ring Structure (for portal mode)
    const portalGroup = new THREE.Group();
    const portalRingCount = 4;
    const portalRings: THREE.Mesh[] = [];

    for (let p = 0; p < portalRingCount; p++) {
      const pInner = 1.1 + p * 0.12;
      const pOuter = pInner + 0.06;
      const pRingGeo = new THREE.RingGeometry(pInner, pOuter, 64);
      const pRingMat = new THREE.MeshBasicMaterial({
        color: p % 2 === 0 ? 0x6366f1 : 0x38bdf8,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0,
        blending: THREE.AdditiveBlending,
      });
      const pRingMesh = new THREE.Mesh(pRingGeo, pRingMat);
      portalGroup.add(pRingMesh);
      portalRings.push(pRingMesh);
    }
    scene.add(portalGroup);

    // Animation Loop
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const render = () => {
      const elapsed = clock.getElapsedTime();

      if (!reducedMotion) {
        if (mode === 'portal') {
          // Flatten globe into portal disk
          globePoints.scale.lerp(new THREE.Vector3(1.3, 1.3, 0.15), 0.06);
          group.rotation.z += 0.04;
          group.rotation.y += 0.02;

          // Resume fades/shrinks into portal center
          resumeGroup.scale.lerp(new THREE.Vector3(0.01, 0.01, 0.01), 0.08);

          // Portal rings spin and intensify
          portalRings.forEach((r, idx) => {
            const mat = r.material as THREE.MeshBasicMaterial;
            mat.opacity = THREE.MathUtils.lerp(mat.opacity, 0.85 - idx * 0.15, 0.08);
            r.rotation.z += 0.02 * (idx % 2 === 0 ? 1 : -1);
          });
        } else {
          // Standard Globe Analysis & Searching mode
          const spinSpeed = mode === 'searching' ? 0.016 : 0.007;
          group.rotation.y += spinSpeed;
          group.rotation.x = Math.sin(elapsed * 0.4) * 0.12;

          // Resume floats gently inside
          resumeGroup.position.y = Math.sin(elapsed * 1.5) * 0.08;
          resumeGroup.rotation.y = Math.sin(elapsed * 0.8) * 0.25;
          resumeGroup.rotation.x = Math.cos(elapsed * 0.6) * 0.1;

          // Reset scale if recovering from portal
          globePoints.scale.lerp(new THREE.Vector3(1, 1, 1), 0.05);
          resumeGroup.scale.lerp(new THREE.Vector3(1, 1, 1), 0.05);

          // Fade out portal rings
          portalRings.forEach((r) => {
            const mat = r.material as THREE.MeshBasicMaterial;
            mat.opacity = THREE.MathUtils.lerp(mat.opacity, 0, 0.1);
          });
        }
      }

      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    // Handle container resize
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      particleGeo.dispose();
      particleMat.dispose();
      particleTexture.dispose();
      ringMat.dispose();
      docGeo.dispose();
      docMat.dispose();
      edgeGeo.dispose();
      edgeMat.dispose();
      lineMat.dispose();
      accentLineMat.dispose();
      portalRings.forEach((r) => {
        r.geometry.dispose();
        (r.material as THREE.Material).dispose();
      });
      renderer.dispose();
    };
  }, [mode, reducedMotion]);

  if (!webglSupported) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center p-8 text-center bg-[#070b16]/80 rounded-full border border-indigo-500/20">
        <div className="w-24 h-32 rounded-lg bg-indigo-950/60 border border-indigo-400/40 flex flex-col p-3 gap-2 shadow-lg shadow-indigo-500/10">
          <div className="w-12 h-2 rounded bg-indigo-400" />
          <div className="w-16 h-1.5 rounded bg-slate-400/60" />
          <div className="w-full h-1 rounded bg-slate-600/40" />
          <div className="w-14 h-1 rounded bg-slate-600/40" />
          <div className="w-10 h-1 rounded bg-slate-600/40" />
        </div>
        <p className="mt-4 text-xs font-mono text-indigo-300">
          {mode === 'portal' ? 'Opening Career Opportunity Portal...' : 'Neural Engine Active (2D Fallback)'}
        </p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative w-full h-full flex items-center justify-center">
      <canvas ref={canvasRef} className="w-full h-full block" />
    </div>
  );
};
