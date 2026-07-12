import * as THREE from 'three';

export class EnvironmentBuilder {
    constructor(scene) {
        this.scene = scene;
        this.meshes = [];
        this.kktPlanes = [];
        this.markers = [];

        // חומר למילוי חצי שקוף של המכשולים
        this.fillMaterial = new THREE.MeshBasicMaterial({
            color: 0x002233,
            transparent: true,
            opacity: 0.6,
            depthWrite: false // Disables depth buffer locking to prevent background blending artifacts from hiding foreground markers
        });
        
        // חומר לקווי המתאר הזוהרים (ללא אלכסונים)
        this.edgeMaterial = new THREE.LineBasicMaterial({
            color: 0x00ffcc,
        });
    }

    teardown() {
        this.meshes.forEach(mesh => {
            mesh.geometry.dispose();
            this.scene.remove(mesh);
        });
        this.meshes = [];
        
        // --- ADDED: Ensure markers are removed on teardown ---
        if (this.markers) {
            this.markers.forEach(m => {
                if (m.material.map) m.material.map.dispose();
                m.material.dispose();
                this.scene.remove(m);
            });
        }
        this.markers = [];
        this.clearKKTPlanes();
    }

    clearKKTPlanes() {
        this.kktPlanes.forEach(plane => {
            plane.geometry.dispose();
            plane.material.dispose();
            this.scene.remove(plane);
        });
        this.kktPlanes = [];
    }

    build(obstacles) {
        obstacles.forEach(obs => {
            let geometry, mesh;

            if (obs.type === "Box") {
                geometry = new THREE.BoxGeometry(obs.b[0] * 2, obs.b[1] * 2, obs.b[2] * 2);
                mesh = new THREE.Mesh(geometry, this.fillMaterial);
                mesh.position.set(...obs.c);
            }
            else if (obs.type === "Sphere") {
                geometry = new THREE.SphereGeometry(obs.r, 20, 20);
                mesh = new THREE.Mesh(geometry, this.fillMaterial);
                mesh.position.set(...obs.c);
            }
            else if (obs.type === "Cylinder") {
                geometry = new THREE.CylinderGeometry(obs.r, obs.r, obs.h * 2, 20);
                mesh = new THREE.Mesh(geometry, this.fillMaterial);
                mesh.position.set(...obs.c);
                mesh.rotation.x = Math.PI / 2;
            }
            else if (obs.type === "HalfSphere") {
                geometry = new THREE.SphereGeometry(obs.sphere.r, 20, 20, 0, Math.PI * 2, 0, Math.PI / 2);
                mesh = new THREE.Mesh(geometry, this.fillMaterial);
                
                // Construct the flat circular base to close the manifold
                const baseGeom = new THREE.CircleGeometry(obs.sphere.r, 20);
                const baseMesh = new THREE.Mesh(baseGeom, this.fillMaterial);
                baseMesh.rotation.x = Math.PI / 2; // Rotate to lie flat on the cutting plane
                
                // Add a Polar Grid to create the concentric "tree ring" internal wireframe
                // 20 radial lines to perfectly align with the dome's segments, and 10 concentric circles
                const polarGrid = new THREE.PolarGridHelper(obs.sphere.r, 20, 10);
                polarGrid.material = this.edgeMaterial; // Overwrite default colors with your glowing cyan
                
                mesh.add(baseMesh);
                mesh.add(polarGrid);

                mesh.position.set(...obs.sphere.c);

                const normal = new THREE.Vector3(...obs.plane.n).normalize();
                const up = new THREE.Vector3(0, 1, 0);
                const quaternion = new THREE.Quaternion().setFromUnitVectors(up, normal);
                mesh.quaternion.copy(quaternion);
            }

            if (mesh) {
                // הוספת קווי המתאר הנקיים על גבי המודל
                const edges = new THREE.EdgesGeometry(geometry);
                const line = new THREE.LineSegments(edges, this.edgeMaterial);
                mesh.add(line);

                this.scene.add(mesh);
                this.meshes.push(mesh);
            }
        });
    }

    renderKKTPlane(point, normal) {
        const geom = new THREE.PlaneGeometry(5, 5);
        const mat = new THREE.MeshBasicMaterial({
            color: 0xff0055, side: THREE.DoubleSide, transparent: true, opacity: 0.6,
        });
        const plane = new THREE.Mesh(geom, mat);
        plane.position.set(...point);

        const nVec = new THREE.Vector3(...normal);
        if (nVec.lengthSq() > 1e-9) {
            nVec.normalize();
            plane.lookAt(new THREE.Vector3().copy(plane.position).add(nVec));
        }
        this.scene.add(plane);
        this.kktPlanes.push(plane);
    }

    renderMarkers(drones, scale = 1.0, tagScale = 1.0) {
        // --- POINT CUSTOMIZATION CONTROLS ---
        const AURA_SIZE = 1.0;      // Glowing aura scale
        const CORE_SIZE = 0.5;      // Solid inner dot ratio (relative to aura)
        const TEXT_SIZE = 40;       // Font size for the text (s1, t1)
        const TEXT_OUTLINE = 5;     // White outline thickness
        const HEIGHT_OFFSET = 1.5;  // Float height above the point
        // ------------------------------------

        const createGlowingDot = (colorHex) => {
            const canvas = document.createElement('canvas');
            canvas.width = 64; canvas.height = 64;
            const ctx = canvas.getContext('2d');
            const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
            
            const coreRatio = Math.min(1.0, Math.max(0.01, CORE_SIZE / AURA_SIZE));
            grad.addColorStop(0, colorHex);
            grad.addColorStop(coreRatio, colorHex);
            grad.addColorStop(1, 'transparent');
            
            ctx.fillStyle = grad;
            ctx.fillRect(0, 0, 64, 64);
            const tex = new THREE.CanvasTexture(canvas);
            const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false });
            const sprite = new THREE.Sprite(mat);
            sprite.renderOrder = 1;
            return sprite;
        };

        const createFloatingText = (text, textColor) => {
            const canvas = document.createElement('canvas');
            canvas.width = 128; canvas.height = 64;
            const ctx = canvas.getContext('2d');
            ctx.font = `bold ${TEXT_SIZE}px Arial`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.lineWidth = TEXT_OUTLINE;
            ctx.strokeStyle = '#ffffff';
            ctx.strokeText(text, 64, 32);
            ctx.fillStyle = textColor;
            ctx.fillText(text, 64, 32);
            
            const tex = new THREE.CanvasTexture(canvas);
            const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false });
            const sprite = new THREE.Sprite(mat);
            sprite.renderOrder = 2;
            return sprite;
        };

        drones.forEach((d, i) => {
            const sPos = d.start.map(p => p * scale);
            const gPos = d.goal.map(p => p * scale);

            const isWithinBounds = (pos) => pos.every(coord => coord > -50 && coord < 150);
            if (!isWithinBounds(sPos) || !isWithinBounds(gPos)) return;

            const sMesh = createGlowingDot('#00ffff');
            sMesh.scale.set(AURA_SIZE * scale, AURA_SIZE * scale, 1);
            sMesh.position.set(...sPos);
            this.scene.add(sMesh);
            
            const sLabel = createFloatingText(`s${i+1}`, '#00ffff');
            sLabel.scale.set(3 * scale * tagScale, 1.5 * scale * tagScale, 1);
            sLabel.position.set(sPos[0], sPos[1], sPos[2] + (HEIGHT_OFFSET * scale));
            this.scene.add(sLabel);
            this.markers.push(sMesh, sLabel);

            const gMesh = createGlowingDot('#ffb86c');
            gMesh.scale.set(AURA_SIZE * scale, AURA_SIZE * scale, 1);
            gMesh.position.set(...gPos);
            this.scene.add(gMesh);
            
            const gLabel = createFloatingText(`t${i+1}`, '#ffb86c');
            gLabel.scale.set(3 * scale * tagScale, 1.5 * scale * tagScale, 1);
            gLabel.position.set(gPos[0], gPos[1], gPos[2] + (HEIGHT_OFFSET * scale));
            this.scene.add(gLabel);
            this.markers.push(gMesh, gLabel);
        });
    }
}