import * as THREE from 'three';

export class EnvironmentBuilder {
    constructor(scene) {
        this.scene = scene;
        this.meshes = [];
        this.markers = [];

        // חומר למילוי חצי שקוף של המכשולים
        this.fillMaterial = new THREE.MeshBasicMaterial({
            color: 0x002233,
            transparent: true,
            opacity: 0.6,
            depthWrite: false, // Standard transparent pipeline: rely on CPU sorting to allow spheres/points to be visible inside them
            premultipliedAlpha: true
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
        
        // --- Clean up both sprite markers and 3D holographic beacons ---
        if (this.markers) {
            this.markers.forEach(m => {
                m.traverse(child => {
                    if (child.geometry) child.geometry.dispose();
                    if (child.material) {
                        if (child.material.map) child.material.map.dispose();
                        child.material.dispose();
                    }
                });
                this.scene.remove(m);
            });
        }
        this.markers = [];
    }

    build(obstacles) {
        obstacles.forEach(obs => {
            let geometry, mesh;

            if (obs.type === "Box") {
                geometry = new THREE.BoxGeometry(obs.b[0] * 2, obs.b[1] * 2, obs.b[2] * 2);
                mesh = new THREE.Mesh(geometry, this.fillMaterial);
                mesh.renderOrder = 3; // Layer 3: Render obstacles over drones and S/G points
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

                // Layer 2: All world transparent objects share this layer for perfect CPU distance sorting
                mesh.traverse((child) => {
                    child.renderOrder = 2; 
                });

                this.scene.add(mesh);
                this.meshes.push(mesh);
            }
        });
    }

    renderMarkers(drones, scale = 1.0, tagScale = 1.0, droneColors = []) {
        // --- POINT CUSTOMIZATION CONTROLS ---
        const POINT_SIZE = 3.0;     // S and G waypoint badges calibrated to 3.0
        const FONT_SIZE = 36;       // Font size for the letter inside the point
        // ------------------------------------

        const dronePaletteHex = [
            '#00ffcc', '#ff5555', '#ffbb00', '#ff00ff', '#00ff66',
            '#5599ff', '#ff8800', '#cc66ff', '#ffff00', '#00bcd4'
        ];

        const createSimplePointWithLetter = (letter, colorHex) => {
            const canvas = document.createElement('canvas');
            canvas.width = 64; canvas.height = 64;
            const ctx = canvas.getContext('2d');
            
            ctx.beginPath();
            ctx.arc(32, 32, 28, 0, Math.PI * 2);
            ctx.fillStyle = '#050510';
            ctx.fill();
            ctx.lineWidth = 6;
            ctx.strokeStyle = colorHex;
            ctx.stroke();
            
            ctx.font = `bold ${FONT_SIZE}px monospace`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = colorHex;
            ctx.fillText(letter, 32, 33);
            
            const tex = new THREE.CanvasTexture(canvas);
            // Layer 10: Render markers consistently after transparent obstacle fills (Layer 2) to eliminate draw-order popping
            const mat = new THREE.SpriteMaterial({ 
                map: tex, 
                transparent: true, 
                depthTest: true, 
                depthWrite: false, 
                blending: THREE.NormalBlending 
            });
            const sprite = new THREE.Sprite(mat);
            sprite.renderOrder = 10;
            return sprite;
        };

        const createHolographicBeacon = (pos, colorHex, letter, droneIdx) => {
            const group = new THREE.Group();
            group.userData = { isBeacon: true, type: letter, droneIndex: droneIdx };
            group.visible = false;

            const colorNum = new THREE.Color(colorHex);
            const ringRadius = 1.35 * scale;

            // 1. Ground Holographic Landing Perimeter
            const floorRingGeom = new THREE.RingGeometry(ringRadius - 0.06 * scale, ringRadius + 0.06 * scale, 32);
            const ringMat = new THREE.MeshBasicMaterial({
                color: colorNum,
                side: THREE.DoubleSide,
                transparent: true,
                opacity: 0.5,
                depthWrite: false
            });
            const floorRing = new THREE.Mesh(floorRingGeom, ringMat);
            floorRing.position.set(pos[0], pos[1], 0.05);
            group.add(floorRing);

            // 2. Waypoint Elevation Halo Ring (Surrounds the drone outside its radius)
            const haloGeom = new THREE.RingGeometry(ringRadius - 0.08 * scale, ringRadius + 0.08 * scale, 32);
            const haloMesh = new THREE.Mesh(haloGeom, ringMat);
            haloMesh.position.set(...pos);
            group.add(haloMesh);

            // 3. Vertical Holographic Laser Rails (Hollow perimeter pillars - 100% open center)
            const beamHeight = Math.max(pos[2], 0.1);
            const lineMat = new THREE.LineBasicMaterial({
                color: colorNum,
                transparent: true,
                opacity: 0.45
            });
            const pillarPoints = [];
            const numPillars = 8;
            for (let p = 0; p < numPillars; p++) {
                const ang = (p / numPillars) * Math.PI * 2;
                const px = pos[0] + Math.cos(ang) * ringRadius;
                const py = pos[1] + Math.sin(ang) * ringRadius;
                pillarPoints.push(px, py, 0.05, px, py, pos[2]);
            }
            const pillarGeom = new THREE.BufferGeometry();
            pillarGeom.setAttribute('position', new THREE.Float32BufferAttribute(pillarPoints, 3));
            const laserPillars = new THREE.LineSegments(pillarGeom, lineMat);
            group.add(laserPillars);

            group.renderOrder = 2;
            return group;
        };

        drones.forEach((d, i) => {
            const sPos = d.start;
            const gPos = d.goal;

            const colorIdx = d.colorIndex !== undefined ? d.colorIndex : i;
            const colorStr = dronePaletteHex[colorIdx % dronePaletteHex.length];

            // 3D Holographic Ground & Altitude Beacons (Active only in 1st person for the tracked drone)
            const sBeacon = createHolographicBeacon(sPos, colorStr, 'S', i);
            sBeacon.userData.point = new THREE.Vector3(...sPos);
            this.scene.add(sBeacon);
            this.markers.push(sBeacon);

            const gBeacon = createHolographicBeacon(gPos, colorStr, 'G', i);
            gBeacon.userData.point = new THREE.Vector3(...gPos);
            this.scene.add(gBeacon);
            this.markers.push(gBeacon);

            // 2D Billboard Letter Badges (Visible in 3rd person / free camera)
            const sMesh = createSimplePointWithLetter('S', colorStr);
            sMesh.userData = { isMarker: true, isMarkerBillboard: true, type: 'S', droneIndex: i, point: new THREE.Vector3(...sPos) };
            sMesh.scale.set(POINT_SIZE * scale, POINT_SIZE * scale, 1);
            sMesh.position.set(...sPos);
            this.scene.add(sMesh);
            this.markers.push(sMesh);

            const gMesh = createSimplePointWithLetter('G', colorStr);
            gMesh.userData = { isMarker: true, isMarkerBillboard: true, type: 'G', droneIndex: i, point: new THREE.Vector3(...gPos) };
            gMesh.scale.set(POINT_SIZE * scale, POINT_SIZE * scale, 1);
            gMesh.position.set(...gPos);
            this.scene.add(gMesh);
            this.markers.push(gMesh);
        });
    }
}