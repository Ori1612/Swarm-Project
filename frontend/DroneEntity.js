import * as THREE from 'three';

export class DroneEntity {
    constructor(scene, trajectoryMatrix, scale, id, tagMin, tagMax, fMin, fMax, hMin, hMax, sMinD, sMaxD, solverType) {
        this.scene = scene;
        this.trajectory = trajectoryMatrix;
        this.solverType = solverType || "SCP"; // Default to SCP if undefined
        this.id = id;
        this.scale = scale;
        this.tagMin = tagMin;
        this.tagMax = tagMax;
        this.fMin = fMin;
        this.fMax = fMax;
        this.hMin = hMin;
        this.hMax = hMax;
        this.scalingMinD = sMinD;
        this.scalingMaxD = sMaxD;
        this.currentFontSize = -1; // Track for re-rendering

        // בניית מודל רחפן (Quadcopter) - גרסה משודרגת, קריאה יותר מרחוק
        const droneGroup = new THREE.Group();
        this.rotorBlades = []; // רפרנס לסיבוב הלהבים ב-update

        // 1. Central Core: Dynamic color
        const coreColor = this.solverType === 'CBS' ? 0xff0000 : 0x66ffff;
        const coreGeom = new THREE.CylinderGeometry(0.22 * this.scale, 0.22 * this.scale, 0.15 * this.scale, 16);
        const coreMat = new THREE.MeshBasicMaterial({ color: coreColor });
        const coreMesh = new THREE.Mesh(coreGeom, coreMat);
        coreMesh.rotation.set(Math.PI / 2, 0, 0); 
        coreMesh.position.set(0, 0, 0); 
        droneGroup.add(coreMesh);

        // Flat Body Disc: Thicker disk, Centered at Z=0
        const bodyGeom = new THREE.CylinderGeometry(0.32 * this.scale, 0.32 * this.scale, 0.08 * this.scale, 16);
        const bodyMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
        const bodyMesh = new THREE.Mesh(bodyGeom, bodyMat);
        bodyMesh.rotation.set(Math.PI / 2, 0, 0); 
        bodyMesh.position.set(0, 0, 0);
        droneGroup.add(bodyMesh);

        // 2. Arms, Rotors, Rotating Blades and Navigation Lights
        const armColorHex = this.solverType === 'CBS' ? 0xff0000 : 0x00aaff;
        const armColor = new THREE.MeshBasicMaterial({ color: armColorHex, transparent: true, opacity: 0.85 });
        const hubMat = new THREE.MeshBasicMaterial({ color: 0x222222 });

        for (let i = 0; i < 4; i++) {
            const angle = (i / 4) * Math.PI * 2 + (Math.PI / 4);

            // Arms: Positioned at Z=0
            const armGeom = new THREE.BoxGeometry(0.85 * this.scale, 0.05 * this.scale, 0.02 * this.scale);
            const armMesh = new THREE.Mesh(armGeom, armColor);
            armMesh.position.set(Math.cos(angle) * 0.42 * this.scale, Math.sin(angle) * 0.42 * this.scale, 0);
            armMesh.rotation.set(0, 0, angle); 
            droneGroup.add(armMesh);

            const rotorX = Math.cos(angle) * 0.75 * this.scale;
            const rotorZ = Math.sin(angle) * 0.75 * this.scale;

            // Hubs: Elevated well above arms
            const hubGeom = new THREE.CylinderGeometry(0.09 * this.scale, 0.09 * this.scale, 0.1 * this.scale, 8);
            const hubMesh = new THREE.Mesh(hubGeom, hubMat);
            hubMesh.rotation.set(Math.PI / 2, 0, 0); 
            hubMesh.position.set(rotorX, rotorZ, 0.05 * this.scale);
            droneGroup.add(hubMesh);

            // Blades: Above hubs
            const bladeGroup = new THREE.Group();
            bladeGroup.position.set(rotorX, rotorZ, 0.12 * this.scale);
            const bladeMat = new THREE.MeshBasicMaterial({
                color: 0x99e6ff, transparent: true, opacity: 0.7, side: THREE.DoubleSide,
            });
            for (let b = 0; b < 2; b++) {
                const bladeGeom = new THREE.BoxGeometry(0.36 * this.scale, 0.05 * this.scale, 0.01 * this.scale);
                const bladeMesh = new THREE.Mesh(bladeGeom, bladeMat);
                bladeMesh.rotation.z = b * (Math.PI / 2);
                bladeGroup.add(bladeMesh);
            }
            droneGroup.add(bladeGroup);
            this.rotorBlades.push(bladeGroup);
        }
        // droneGroup stays naturally in Z-up
        this.mesh = droneGroup;
        this.scene.add(this.mesh);

        this.currentPosition = new THREE.Vector3();
        this.currentVelocity = new THREE.Vector3(1, 0, 0);

        this.pathHistory = [];
        this.maxTrailPoints = 20;
        this.trailMesh = null;
        this.trailMaterial = new THREE.MeshBasicMaterial({
            color: armColorHex, transparent: true, opacity: 0.5,
        });

        this.lastTrailUpdatePos = new THREE.Vector3(Infinity, Infinity, Infinity);
        this.rebuildThreshold = 0.2 * this.scale;

        // --- NAME TAG CONFIG ---
        this.heightOffset = 5; // Change this number to move the tag higher or lower
        this.nameTag = this.createNameTag(`Drone ${this.id}`);
        this.mesh.add(this.nameTag);
    }

    createNameTag(text) {
        const canvas = document.createElement('canvas');
        canvas.width = 128; canvas.height = 64;
        const ctx = canvas.getContext('2d');
        // Dark tactical background
        ctx.fillStyle = 'rgba(0, 20, 40, 0.9)';
        ctx.fillRect(0, 0, 128, 64);
        // Cyan border
        ctx.strokeStyle = '#00ffcc';
        ctx.lineWidth = 4;
        ctx.strokeRect(2, 2, 124, 60);
        // Cyan text
        ctx.fillStyle = '#00ffcc';
        ctx.font = `bold ${this.fontSize}px monospace`;
        ctx.textAlign = 'center';
        ctx.fillText(text, 64, 40);
        
        const texture = new THREE.CanvasTexture(canvas);
        const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
        const sprite = new THREE.Sprite(spriteMaterial);
        sprite.scale.set(this.tagScale, this.tagScale / 2, 1);
        
        // FIX: Anchor to the Z-axis (Up) instead of the Y-axis (Horizontal)
        sprite.position.z = this.heightOffset; 
        
        return sprite;
    }

    updateNameTagTexture(text, fontSize) {
        const ctx = this.nameTag.material.map.image.getContext('2d');
        ctx.clearRect(0, 0, 128, 64);
        ctx.fillStyle = 'rgba(0, 20, 40, 0.9)';
        ctx.fillRect(0, 0, 128, 64);
        ctx.strokeStyle = '#00ffcc';
        ctx.lineWidth = 4;
        ctx.strokeRect(2, 2, 124, 60);
        ctx.fillStyle = '#00ffcc';
        
        // If the text is longer than 7 characters (like "Drone 10"), shrink it slightly
        const displayFontSize = text.length > 7 ? fontSize * 0.9 : fontSize;
        
        ctx.font = `bold ${displayFontSize}px monospace`;
        ctx.textAlign = 'center';
        ctx.fillText(text, 64, 40);
        this.nameTag.material.map.needsUpdate = true;
    }

    update(timeFloat, cameraDistance) {
        // Dynamic Scaling Logic
        // Scale proportionally between 100 (start of zoom-out) and 200 (max distance)
        // Values stay at their minimums below 100.
        const dist = cameraDistance || 50; 
        const t = Math.max(0, Math.min(1, (dist - this.scalingMinD) / (this.scalingMaxD - this.scalingMinD)));

        // Apply dynamic calculation using the ranges configured in UIManager
        const currentTagSize = this.tagMin + (t * (this.tagMax - this.tagMin));
        const currentHeight = this.hMin + (t * (this.hMax - this.hMin));
        const currentFontSize = Math.round(this.fMin + (t * (this.fMax - this.fMin)));

        // Apply to nameTag
        if (this.nameTag) {
            this.nameTag.scale.set(currentTagSize, currentTagSize / 2, 1);
            this.nameTag.position.z = currentHeight;

            // Only re-render if font size actually changed to save performance
            if (currentFontSize !== this.currentFontSize) {
                this.currentFontSize = currentFontSize;
                this.updateNameTagTexture(`Drone ${this.id}`, currentFontSize);
            }
        }

        const T_max = this.trajectory.length - 1;
        const tIndex = Math.max(0, Math.min(T_max, timeFloat));

        const idx = Math.floor(tIndex);
        const nextIdx = Math.min(idx + 1, T_max);
        const alpha = tIndex - idx;

        const p1 = this.trajectory[idx];
        const p2 = this.trajectory[nextIdx];

        this.currentPosition.set(
            p1[0] + (p2[0] - p1[0]) * alpha,
            p1[1] + (p2[1] - p1[1]) * alpha,
            p1[2] + (p2[2] - p1[2]) * alpha
        );
        this.mesh.position.copy(this.currentPosition);

        if (idx > 0) {
            const prev = this.trajectory[idx - 1];
            const dx = p1[0] - prev[0], dy = p1[1] - prev[1], dz = p1[2] - prev[2];
            if (dx !== 0 || dy !== 0 || dz !== 0) {
                this.currentVelocity.set(dx, dy, dz).normalize();
            }
        }

        // Fix: Use Vy and Vx to calculate heading in the XY plane
        const vx = this.currentVelocity.x;
        const vy = this.currentVelocity.y;

        if (vx !== 0 || vy !== 0) {
            // Correct rotation around Z for heading
            this.mesh.rotation.set(0, 0, Math.atan2(vy, vx));
        }

        // סיבוב הלהבים (Spinning around the Z-axis, which is the drone's 'up' vector)
        const spinSpeed = timeFloat * 25;
        this.rotorBlades.forEach((blade, i) => {
            blade.rotation.z = spinSpeed * (i % 2 === 0 ? 1 : -1);
        });

    }

    dispose() {
        this.mesh.traverse((child) => {
            if (child.isMesh) {
                child.geometry.dispose();
                child.material.dispose();
            }
        });
        this.scene.remove(this.mesh);
        
        // Trail disposal logic is no longer necessary, but left for safety

        if (this.nameTag) {
            this.nameTag.material.map.dispose();
            this.nameTag.material.dispose();
        }
        this.pathHistory = [];
        this.trailMesh = null;
    }
}