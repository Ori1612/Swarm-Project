import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { DroneEntity } from './DroneEntity.js';

export class SceneManager {
    constructor() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x050510);

        this.camera = new THREE.PerspectiveCamera(
            60, window.innerWidth / window.innerHeight, 0.1, 5000
        );
        // הגדרת Z כציר הגובה כדי להתאים לפיזיקה של השרת
        this.camera.up.set(0, 0, 1); 
        
        // Tuning: Change these coordinates to set the default startup view
        const initialCameraPos = new THREE.Vector3(60, 60, 60); 
        this.camera.position.copy(initialCameraPos);

        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        document.body.appendChild(this.renderer.domElement);

        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.08;
        this.controls.enableRotate = true;
        this.controls.enablePan = true;
        this.controls.screenSpacePanning = true;
        this.controls.maxPolarAngle = Math.PI;
        
        // Zoom Limits
        this.controls.minDistance = 5;   // The closest you can zoom in
        this.controls.maxDistance = 200; // The furthest you can zoom out

        this.controls.target.set(0, 0, 0);
        this.defaultPivot = new THREE.Vector3(0, 0, 0);
        
        // Configuration: Change these to adjust 3rd person view
        // (-10 = behind, 0 = side, 10 = height)
        this.thirdPersonOffset = new THREE.Vector3(-10, 0, 10);

        // Reset the rotation pivot to the environment center upon double-click
        window.addEventListener('dblclick', () => {
            this.controls.target.copy(this.defaultPivot);
            this.controls.update();
        });

        this.gridHelper = null;
        this.drones = []; // The SceneManager now owns the physical entities

        this.scene.add(new THREE.AmbientLight(0xffffff, 0.6));
        const key = new THREE.PointLight(0x00ffcc, 1.2, 0);
        key.position.set(120, 160, 120);
        this.scene.add(key);
        const fill = new THREE.PointLight(0xff8800, 0.6, 0);
        fill.position.set(-80, -40, -80);
        this.scene.add(fill);

        window.addEventListener('resize', () => {
            this.camera.aspect = window.innerWidth / window.innerHeight;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(window.innerWidth, window.innerHeight);
        });
    }

    frameBounds(lo, hi) {
        const center = new THREE.Vector3((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2);
        const sizeX = hi[0] - lo[0];
        const sizeY = hi[1] - lo[1];
        const maxDim = Math.max(sizeX, sizeY, 20);

        // Store the default pivot permanently (true 3D geometric center)
        this.defaultPivot.copy(center);

        // Set the pivot to the true 3D geometric center
        this.controls.target.copy(this.defaultPivot);
        this.controls.update();

        // Only auto-position the camera if we aren't loading a custom profile view
        if (!this.hasCustomCameraView) {
            this.camera.position.set(maxDim, maxDim, maxDim * 0.8);
            this.camera.updateProjectionMatrix();
        }

        if (this.gridGroup) {
            this.scene.remove(this.gridGroup);
            this.gridGroup.traverse(child => { if (child.geometry) child.geometry.dispose(); if (child.material) child.material.dispose(); });
        }
        this.gridGroup = new THREE.Group();

        // 1. Manually build Grid Lines (Clean and flicker-free)
        // Change the color to a higher-contrast blue and boost opacity for better visibility
        const gridMaterial = new THREE.LineBasicMaterial({ 
            color: 0x0088cc, 
            transparent: true, 
            opacity: 0.7 
        });
        const gridLines = new THREE.BufferGeometry();
        const points = [];
        const div = 10;
        for (let i = 0; i <= div; i++) {
            const x = lo[0] + (i / div) * sizeX;
            const y = lo[1] + (i / div) * sizeY;
            points.push(x, lo[1], lo[2], x, hi[1], lo[2]);
            points.push(lo[0], y, lo[2], hi[0], y, lo[2]);
        }
        gridLines.setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
        const gridMesh = new THREE.LineSegments(gridLines, gridMaterial);
        
        // Align grid to environment floor
        gridMesh.position.set(0, 0, 0); 
        this.gridGroup.add(gridMesh);

        this.scene.add(this.gridGroup);
    }

    updateCameraTracking(targetDrone, mode) {
        if (mode === 'free' || !targetDrone) return;

        if (mode === '3rd') {
            // DEBUG: Open your F12 console. If you see this spamming, 
            // the code is running and you can tune the offset below.
            console.log("Tracking 3rd person..."); 
            
            const heading = Math.atan2(targetDrone.currentVelocity.y, targetDrone.currentVelocity.x);
            
            // Hardcoded values to bypass cache issues. Change these numbers:
            // 1st param: Distance behind drone (-10 is closer, -20 is further)
            // 2nd param: Side offset (0 is centered)
            // 3rd param: Height (10 is higher, 5 is lower)
            const offset = new THREE.Vector3(-10, 0, 10) 
                .applyAxisAngle(new THREE.Vector3(0, 0, 1), heading);
                
            this.camera.position.copy(targetDrone.currentPosition).add(offset);
            this.camera.lookAt(targetDrone.currentPosition);
        }
        else if (mode === '1st') {
            this.camera.position.copy(targetDrone.currentPosition);
            const lookTarget = new THREE.Vector3()
                .copy(targetDrone.currentPosition).add(targetDrone.currentVelocity);
            this.camera.lookAt(lookTarget);
        }
    }

    loadDrones(trajectories, scaleMultiplier, sMinD, sMaxD, tMin, tMax, fMin, fMax, hMin, hMax) {
        this.clearDrones();
        trajectories.forEach((item, index) => {
            // item is {solver: "...", path: [...]}
            this.drones.push(new DroneEntity(
                this.scene, item.path, scaleMultiplier, index + 1, 
                tMin, tMax, fMin, fMax, hMin, hMax, sMinD, sMaxD, item.solver
            ));
        });
    }

    updateDrones(timeValues) {
        if (this.drones.length === 0) return;

        const distance = (this.controls && typeof this.controls.getDistance === 'function') 
            ? this.controls.getDistance() 
            : 50;
        
        const times = Array.isArray(timeValues) ? timeValues : [timeValues, timeValues];
        
        this.drones.forEach((drone, index) => {
            const t = times[index] !== undefined ? times[index] : times[0];
            drone.update(t, distance);
        });
    }

    clearDrones() {
        this.drones.forEach(d => d.dispose());
        this.drones = [];
    }

    updateCameraLimits(min, max) {
        this.controls.minDistance = min;
        this.controls.maxDistance = max;
        this.controls.update();
    }

    setCameraView(position, target, zoom) {
        this.camera.position.set(position.x, position.y, position.z);
        this.controls.target.set(target.x, target.y, target.z);
        
        if (zoom) {
            // Calculate direction from target to camera
            const direction = new THREE.Vector3().subVectors(position, target).normalize();
            this.camera.position.copy(target).add(direction.multiplyScalar(zoom));
        }
        
        this.controls.update();
    }

    getDrone(index) {
        return this.drones[index];
    }

    getDroneMeshes() {
        return this.drones.map(d => d.mesh);
    }

    render() {
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
}