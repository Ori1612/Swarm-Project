import * as THREE from 'three';

export class DroneEntity {
    constructor(scene, trajectoryMatrix, scale, id, tagMin, tagMax, fMin, fMax, hMin, hMax, sMinD, sMaxD, solverType, droneColor, customName, serverFailureFrame = null, targetStart = null, targetGoal = null) {
        this.scene = scene;
        this.trajectory = trajectoryMatrix;
        this.solverType = solverType || "SCP";
        this.id = id;
        this.scale = scale;
        this.targetStart = targetStart ? new THREE.Vector3(...targetStart) : new THREE.Vector3(...this.trajectory[0]);
        this.targetGoal = targetGoal ? new THREE.Vector3(...targetGoal) : new THREE.Vector3(...this.trajectory[this.trajectory.length - 1]);
        this.tagMin = tagMin;
        this.tagMax = tagMax;
        this.fMin = fMin;
        this.fMax = fMax;
        this.hMin = hMin;
        this.hMax = hMax;
        this.scalingMinD = sMinD;
        this.scalingMaxD = sMaxD;
        this.currentFontSize = -1;
        this.droneColor = droneColor || 0x00ffcc;

        const droneGroup = new THREE.Group();
        this.rotorBlades = [];

        // 1. Central Core: Unique per-drone theme color (Radius: 0.20, Height: 0.15)
        const coreGeom = new THREE.CylinderGeometry(0.20 * this.scale, 0.20 * this.scale, 0.15 * this.scale, 16);
        const coreMat = new THREE.MeshBasicMaterial({ color: this.droneColor });
        const coreMesh = new THREE.Mesh(coreGeom, coreMat);
        coreMesh.rotation.set(Math.PI / 2, 0, 0); 
        coreMesh.position.set(0, 0, 0); 
        droneGroup.add(coreMesh);
        this.coreMesh = coreMesh;

        // Flat Body Disc (Radius: 0.30, Height: 0.08)
        const bodyGeom = new THREE.CylinderGeometry(0.30 * this.scale, 0.30 * this.scale, 0.08 * this.scale, 16);
        const bodyMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
        const bodyMesh = new THREE.Mesh(bodyGeom, bodyMat);
        bodyMesh.rotation.set(Math.PI / 2, 0, 0); 
        bodyMesh.position.set(0, 0, 0);
        droneGroup.add(bodyMesh);
        this.bodyMesh = bodyMesh;

        // 2. Arms, Rotors, Rotating Blades and Navigation Lights
        const armColor = new THREE.MeshBasicMaterial({ color: this.droneColor });
        const hubMat = new THREE.MeshBasicMaterial({ color: 0x222222 });
        this.armMeshes = [];
        this.hubMeshes = [];

        for (let i = 0; i < 4; i++) {
            const angle = (i / 4) * Math.PI * 2 + (Math.PI / 4);

            // Arms: Length = 0.80, outer edge reaches radius 0.80 (strictly <= 1.00)
            const armGeom = new THREE.BoxGeometry(0.80 * this.scale, 0.05 * this.scale, 0.02 * this.scale);
            const armMesh = new THREE.Mesh(armGeom, armColor);
            armMesh.position.set(Math.cos(angle) * 0.40 * this.scale, Math.sin(angle) * 0.40 * this.scale, 0);
            armMesh.rotation.set(0, 0, angle); 
            droneGroup.add(armMesh);
            this.armMeshes.push(armMesh);

            const rotorX = Math.cos(angle) * 0.70 * this.scale;
            const rotorZ = Math.sin(angle) * 0.70 * this.scale;

            // Hubs: Positioned at radius 0.70, outer radius = 0.78 (strictly <= 1.00)
            const hubGeom = new THREE.CylinderGeometry(0.08 * this.scale, 0.08 * this.scale, 0.10 * this.scale, 8);
            const hubMesh = new THREE.Mesh(hubGeom, hubMat);
            hubMesh.rotation.set(Math.PI / 2, 0, 0); 
            hubMesh.position.set(rotorX, rotorZ, 0.05 * this.scale);
            droneGroup.add(hubMesh);
            this.hubMeshes.push(hubMesh);

            // Blades: Span = 0.44, maximum tip reaches radius 0.70 + 0.22 = 0.92 (strictly <= 1.00)
            const bladeGroup = new THREE.Group();
            bladeGroup.position.set(rotorX, rotorZ, 0.12 * this.scale);
            const bladeMat = new THREE.MeshBasicMaterial({
                color: 0x99e6ff, transparent: true, opacity: 0.45, side: THREE.DoubleSide,
            });
            for (let b = 0; b < 2; b++) {
                const bladeGeom = new THREE.BoxGeometry(0.44 * this.scale, 0.05 * this.scale, 0.01 * this.scale);
                const bladeMesh = new THREE.Mesh(bladeGeom, bladeMat);
                bladeMesh.rotation.z = b * (Math.PI / 2);
                bladeGroup.add(bladeMesh);
            }
            droneGroup.add(bladeGroup);
            this.rotorBlades.push(bladeGroup);
        }

        // Bounding Sphere: Exact physical collision hull radius (1.00)
        const sphereRadius = 1.00 * this.scale;
        const sphereGeom = new THREE.SphereGeometry(sphereRadius, 16, 16);
        
        this.currentSphereOpacity = 0.30;
        this.boundingSphereMaterial = new THREE.MeshBasicMaterial({
            color: this.droneColor,
            opacity: Math.pow(0.30, 2.2),
            transparent: true,
            wireframe: true,
            side: THREE.DoubleSide,
            depthWrite: false
        });
        this.boundingSphereMesh = new THREE.Mesh(sphereGeom, this.boundingSphereMaterial);
        droneGroup.add(this.boundingSphereMesh);

        // Layer 1: Cascade render layers to ALL opaque solid child meshes
        droneGroup.traverse((child) => {
            if (child.isMesh) {
                child.renderOrder = 1; // Drone solid bodies write depth and render first
            }
        });
        // Layer 4: Render bounding spheres after transparent obstacle fills (Layer 2) so obstacle transparency never darkens or tints the sphere in the foreground
        this.boundingSphereMesh.renderOrder = 4;

        // 3. Precision CAD Anchor & Ground Crosshair (Vision 3 - Solid 3D Laser Beam)
        const cadGroup = new THREE.Group();
        cadGroup.frustumCulled = false;

        const laserMat = new THREE.MeshBasicMaterial({
            color: this.droneColor,
            transparent: true,
            opacity: 0.75,
            depthWrite: false
        });

        // Volumetric Laser Cylinder (unit height, scaled dynamically in update)
        const laserGeom = new THREE.CylinderGeometry(0.04 * this.scale, 0.04 * this.scale, 1.0, 8);
        const plumbBeam = new THREE.Mesh(laserGeom, laserMat);
        plumbBeam.rotation.x = Math.PI / 2; // Align along Z axis
        plumbBeam.frustumCulled = false;
        cadGroup.add(plumbBeam);
        this.cadPlumbBeam = plumbBeam;

        // Ground Crosshair (+)
        const lineMat = new THREE.LineBasicMaterial({
            color: this.droneColor,
            transparent: true,
            opacity: 0.85,
        });
        const crosshairGeom = new THREE.BufferGeometry();
        const tickSize = 0.60 * this.scale;
        const crossPoints = [
            -tickSize, 0, 0,   tickSize, 0, 0,
            0, -tickSize, 0,   0, tickSize, 0
        ];
        crosshairGeom.setAttribute('position', new THREE.Float32BufferAttribute(crossPoints, 3));
        const crosshairMesh = new THREE.LineSegments(crosshairGeom, lineMat);
        crosshairMesh.frustumCulled = false;

        // Ground Reticle Ring
        const reticleGeom = new THREE.RingGeometry(0.12 * this.scale, 0.16 * this.scale, 24);
        const reticleMat = new THREE.MeshBasicMaterial({
            color: this.droneColor,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.85,
            depthWrite: false
        });
        const reticleMesh = new THREE.Mesh(reticleGeom, reticleMat);
        reticleMesh.frustumCulled = false;

        const groundAnchor = new THREE.Group();
        groundAnchor.frustumCulled = false;
        groundAnchor.add(crosshairMesh);
        groundAnchor.add(reticleMesh);
        cadGroup.add(groundAnchor);
        this.cadGroundAnchor = groundAnchor;

        cadGroup.visible = false;
        this.cadGroup = cadGroup;
        this.scene.add(this.cadGroup);

        this.mesh = droneGroup;
        this.scene.add(this.mesh);

        this.currentPosition = new THREE.Vector3();
        this.currentVelocity = new THREE.Vector3(1, 0, 0);

        this.pathHistory = [];
        this.maxTrailPoints = 20;
        this.trailMesh = null;
        this.trailMaterial = new THREE.MeshBasicMaterial({
            color: this.droneColor, transparent: true, opacity: 0.5,
        });

        this.lastTrailUpdatePos = new THREE.Vector3(Infinity, Infinity, Infinity);
        this.rebuildThreshold = 0.2 * this.scale;

        // --- ALGORITHMIC WATCHDOG (FAILURE DETECTION) ---
        this.failureFrame = (serverFailureFrame !== null && serverFailureFrame !== undefined)
            ? serverFailureFrame
            : Infinity;
        this.isFailedState = false;

        const isMacroEnv = this.trajectory.some(p => p[0] > 25 || p[1] > 25 || p[2] > 25);
        const envBound = isMacroEnv ? 100.0 : 20.0;
        const margin = 0.05;
        const maxStep = isMacroEnv ? 20.0 : 4.0;

        for (let i = 0; i < this.trajectory.length; i++) {
            const p = this.trajectory[i];
            const isOutOfBounds = (
                p[0] < margin || p[0] > (envBound - margin) ||
                p[1] < margin || p[1] > (envBound - margin) ||
                p[2] < margin || p[2] > (envBound - margin) ||
                !Number.isFinite(p[0]) || !Number.isFinite(p[1]) || !Number.isFinite(p[2])
            );

            if (isOutOfBounds) {
                this.failureFrame = Math.min(this.failureFrame, Math.max(0, i - 1));
                break;
            }

            // Detect unphysical teleportation jumps between consecutive frames
            if (i > 0) {
                const prev = this.trajectory[i - 1];
                const stepLen = Math.hypot(p[0] - prev[0], p[1] - prev[1], p[2] - prev[2]);
                if (stepLen > maxStep) {
                    this.failureFrame = Math.min(this.failureFrame, Math.max(0, i - 1));
                    break;
                }
            }

            // Detect stagnation / local minimum traps
            if (i > 5) {
                const pOld = this.trajectory[i - 5];
                const distMoved = Math.hypot(p[0] - pOld[0], p[1] - pOld[1], p[2] - pOld[2]);
                if (distMoved < 0.05) {
                    const endP = this.trajectory[this.trajectory.length - 1];
                    const distToEnd = Math.hypot(p[0] - endP[0], p[1] - endP[1], p[2] - endP[2]);
                    if (distToEnd > 2.0) {
                        this.failureFrame = Math.min(this.failureFrame, Math.max(0, i - 5));
                        break;
                    }
                }
            }
        }

        // --- NAME TAG CONFIG ---
        this.heightOffset = 5; // Change this number to move the tag higher or lower
        this.displayName = customName || `Drone ${this.id}`;
        this.tagScale = this.tagMin || 1.0;
        this.fontSize = this.fMin || 16;
        this.nameTag = this.createNameTag(this.displayName);
        this.nameTag.renderOrder = 999;
        this.mesh.add(this.nameTag);
    }

    createNameTag(text) {
        const canvas = document.createElement('canvas');
        canvas.width = 128; canvas.height = 64;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'rgba(0, 20, 40, 0.9)';
        ctx.fillRect(0, 0, 128, 64);
        
        const hexColorStr = '#' + new THREE.Color(this.droneColor).getHexString();
        ctx.strokeStyle = hexColorStr;
        ctx.lineWidth = 4;
        ctx.strokeRect(2, 2, 124, 60);
        ctx.fillStyle = hexColorStr;
        ctx.font = `bold ${this.fontSize}px monospace`;
        ctx.textAlign = 'center';
        ctx.fillText(text, 64, 40);
        
        const texture = new THREE.CanvasTexture(canvas);
        // HUD Overlay: depthTest: false and high renderOrder ensure the nameplate is always visible on top of all 3D geometry and obstacle lines
        const spriteMaterial = new THREE.SpriteMaterial({ 
            map: texture, 
            transparent: true, 
            depthTest: false, 
            depthWrite: false,
            blending: THREE.NormalBlending
        });
        const sprite = new THREE.Sprite(spriteMaterial);
        sprite.renderOrder = 999;
        sprite.scale.set(this.tagScale, this.tagScale / 2, 1);
        sprite.position.z = this.heightOffset; 
        
        return sprite;
    }

    updateNameTagTexture(text, fontSize) {
        const ctx = this.nameTag.material.map.image.getContext('2d');
        ctx.clearRect(0, 0, 128, 64);
        ctx.fillStyle = 'rgba(0, 20, 40, 0.9)';
        ctx.fillRect(0, 0, 128, 64);
        
        const hexColorStr = '#' + new THREE.Color(this.droneColor).getHexString();
        ctx.strokeStyle = this.isFailedState ? '#ff0044' : hexColorStr;
        ctx.lineWidth = 4;
        ctx.strokeRect(2, 2, 124, 60);
        ctx.fillStyle = this.isFailedState ? '#ff0044' : hexColorStr;
        
        const displayFontSize = text.length > 7 ? fontSize * 0.9 : fontSize;
        
        // Dynamic control for Failure text size
        const failureFontSize = displayFontSize * 0.8; 
        
        ctx.textAlign = 'center';
        
        if (this.isFailedState) {
            ctx.font = `bold ${failureFontSize}px monospace`;
            ctx.fillText("Failure", 64, 26);
            ctx.fillText("Detected", 64, 52);
        } else {
            ctx.font = `bold ${displayFontSize}px monospace`;
            ctx.fillText(text, 64, 40);
        }
        this.nameTag.material.map.needsUpdate = true;
    }

    update(timeFloat, cameraDistance) {
        let renderTime = timeFloat;
        let showFailure = false;
        if (timeFloat >= this.failureFrame) {
            renderTime = this.failureFrame;
            showFailure = true;
        }

        if (showFailure !== this.isFailedState) {
            this.isFailedState = showFailure;
            this.currentFontSize = -1; // Force immediate re-render
        }

        // Dynamic Scaling Logic
        // Scale proportionally between scalingMinD and scalingMaxD based on scenario profile settings
        const dist = cameraDistance || 50; 
        const t = Math.max(0, Math.min(1, (dist - this.scalingMinD) / (this.scalingMaxD - this.scalingMinD)));

        // Apply dynamic calculation using the ranges configured in UIManager profiles
        let currentTagSize = this.tagMin + (t * (this.tagMax - this.tagMin));
        let currentHeight = this.hMin + (t * (this.hMax - this.hMin));
        const currentFontSize = Math.round(this.fMin + (t * (this.fMax - this.fMin)));

        // In 3rd person tracking: cut badge size in half (0.5x) and reduce height offset to one third (1/3x)
        if (this.isThirdPersonActive) {
            currentTagSize *= 0.50;
            currentHeight = currentHeight / 3.0;
        }

        // Apply to nameTag
        if (this.nameTag) {
            this.nameTag.scale.set(currentTagSize, currentTagSize / 2, 1);
            this.nameTag.position.z = currentHeight;

            // Only re-render if font size actually changed to save performance
            if (currentFontSize !== this.currentFontSize) {
                this.currentFontSize = currentFontSize;
                this.updateNameTagTexture(this.displayName, currentFontSize);
            }
        }

        const T_max = this.trajectory.length - 1;
        const tIndex = Math.max(0, Math.min(T_max, renderTime));

        const idx = Math.floor(tIndex);
        const nextIdx = Math.min(idx + 1, T_max);
        const alpha = tIndex - idx;

        const p1 = this.trajectory[idx];
        const p2 = this.trajectory[nextIdx];

        const isMacro = this.trajectory.some(p => p[0] > 25 || p[1] > 25 || p[2] > 25);
        const maxBound = isMacro ? 100.0 : 20.0;
        this.currentPosition.set(
            Math.max(0, Math.min(maxBound, p1[0] + (p2[0] - p1[0]) * alpha)),
            Math.max(0, Math.min(maxBound, p1[1] + (p2[1] - p1[1]) * alpha)),
            Math.max(0, Math.min(maxBound, p1[2] + (p2[2] - p1[2]) * alpha))
        );
        this.mesh.position.copy(this.currentPosition);

        let dx = p2[0] - p1[0];
        let dy = p2[1] - p1[1];
        let dz = p2[2] - p1[2];
        if (dx === 0 && dy === 0 && dz === 0 && idx > 0) {
            const prev = this.trajectory[idx - 1];
            dx = p1[0] - prev[0];
            dy = p1[1] - prev[1];
            dz = p1[2] - prev[2];
        }
        if (dx !== 0 || dy !== 0 || dz !== 0) {
            this.currentVelocity.set(dx, dy, dz).normalize();
        }

        // Fix: Use Vy and Vx to calculate heading in the XY plane
        const vx = this.currentVelocity.x;
        const vy = this.currentVelocity.y;

        if (vx !== 0 || vy !== 0) {
            // Correct rotation around Z for heading
            this.mesh.rotation.set(0, 0, Math.atan2(vy, vx));
        }

        // Strict Docking Detection: Dock indicators require an error-free trajectory and actual target arrival
        const distToStart = this.currentPosition.distanceTo(this.targetStart);
        const distToGoal = this.currentPosition.distanceTo(this.targetGoal);
        const dockTol = 0.15 * this.scale;

        const atStart = !this.isFailedState && (renderTime <= 1e-3) && (distToStart < dockTol);
        const atGoal = !this.isFailedState && (this.failureFrame === Infinity) && (distToGoal < dockTol) && (renderTime >= T_max - 1e-3);
        const isDocked = atStart || atGoal;
        this.isDocked = isDocked;

        if (this.cadGroup) {
            this.cadGroup.visible = isDocked;
            if (isDocked) {
                const zHeight = Math.max(0.05, this.currentPosition.z - 0.05);
                this.cadPlumbBeam.scale.set(1, zHeight, 1);
                this.cadPlumbBeam.position.set(
                    this.currentPosition.x,
                    this.currentPosition.y,
                    0.05 + (zHeight / 2)
                );
                this.cadGroundAnchor.position.set(
                    this.currentPosition.x,
                    this.currentPosition.y,
                    0.05
                );
            }
        }

        // Blades spin during flight; idle stop when docked at waypoint or in failed state
        const spinSpeed = (isDocked || this.isFailedState) ? 0 : (renderTime * 25);
        this.rotorBlades.forEach((blade, i) => {
            blade.rotation.z = spinSpeed * (i % 2 === 0 ? 1 : -1);
        });

    }

    setFirstPersonMode(isFPV) {
        this.isFirstPerson = isFPV;
        if (this.coreMesh) this.coreMesh.visible = !isFPV;
        if (this.bodyMesh) this.bodyMesh.visible = !isFPV;
        if (this.boundingSphereMesh) {
            this.boundingSphereMesh.visible = !isFPV && (this.currentSphereOpacity > 0.001);
        }
        if (this.nameTag) {
            this.nameTag.visible = !isFPV;
        }

        // In 1st person cockpit, display both front arms/rotors (indices 0 & 3) symmetrically
        if (this.armMeshes) {
            this.armMeshes.forEach((arm, i) => {
                arm.visible = isFPV ? (i === 0 || i === 3) : true;
            });
        }
        if (this.hubMeshes) {
            this.hubMeshes.forEach((hub, i) => {
                hub.visible = isFPV ? (i === 0 || i === 3) : true;
            });
        }
        if (this.rotorBlades) {
            this.rotorBlades.forEach((blade, i) => {
                blade.visible = isFPV ? (i === 0 || i === 3) : true;
            });
        }
    }

    setSphereOpacity(opacity) {
        this.currentSphereOpacity = Math.max(0, Math.min(1, opacity));
        if (this.boundingSphereMaterial && this.boundingSphereMesh) {
            // Perceptual gamma 2.2 curve maps linear human eye perception evenly across the 0.0 to 1.0 slider range
            this.boundingSphereMaterial.opacity = Math.pow(this.currentSphereOpacity, 2.2);
            this.boundingSphereMaterial.color.setHex(this.droneColor);
            this.boundingSphereMesh.visible = (this.currentSphereOpacity > 0.001) && !this.isFirstPerson;
        }
    }

    dispose() {
        this.mesh.traverse((child) => {
            if (child.isMesh) {
                child.geometry.dispose();
                child.material.dispose();
            }
        });
        this.scene.remove(this.mesh);

        if (this.cadGroup) {
            this.cadGroup.traverse((child) => {
                if (child.geometry) child.geometry.dispose();
                if (child.material) child.material.dispose();
            });
            this.scene.remove(this.cadGroup);
        }

        if (this.nameTag) {
            this.nameTag.material.map.dispose();
            this.nameTag.material.dispose();
        }
        this.pathHistory = [];
        this.trailMesh = null;
    }
}