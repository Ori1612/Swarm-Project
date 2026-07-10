import * as THREE from 'three';

export class EnvironmentBuilder {
    constructor(scene) {
        this.scene = scene;
        this.meshes = [];
        this.kktPlanes = [];

        // חומר למילוי חצי שקוף של המכשולים
        this.fillMaterial = new THREE.MeshBasicMaterial({
            color: 0x002233,
            transparent: true,
            opacity: 0.6,
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
}