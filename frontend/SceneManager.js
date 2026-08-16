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
        this.trackedHeading = null;
        this.lastTrackedDrone = null;
        this.lastTrackedMode = null;

        this.defaultCameraPos = null;
        this.defaultCameraTarget = null;
        this.defaultZoom = null;

        // Reset the rotation pivot and default scenario view upon double-click (in free camera only)
        window.addEventListener('dblclick', (e) => {
            if (e.target.closest('#ui-container') || e.target.closest('#mini-ui-container')) return;
            if (this.lastTrackedMode === '1st' || this.lastTrackedMode === '3rd') return;

            if (this.defaultCameraPos && this.defaultCameraTarget) {
                this.setCameraView(this.defaultCameraPos, this.defaultCameraTarget, this.defaultZoom);
            } else {
                this.controls.target.copy(this.defaultPivot);
                this.controls.update();
            }
        });

        this.gridHelper = null;
        this.drones = []; // The SceneManager now owns the physical entities
        this.nameplatesVisible = true;

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
        // Configure drone visibility and nameplate states based on camera mode and global toggle
        this.drones.forEach(d => {
            d.isThirdPersonActive = (mode === '3rd' && d === targetDrone);
            if (d.mesh) d.mesh.visible = true;
            if (d.setFirstPersonMode) d.setFirstPersonMode(false);

            if (d.nameTag) {
                if (!this.nameplatesVisible || mode === '1st') {
                    d.nameTag.visible = false;
                } else if (mode === '3rd') {
                    // In 3rd person, display ONLY the active tracked drone's nameplate
                    d.nameTag.visible = (d === targetDrone);
                } else {
                    d.nameTag.visible = true;
                }
            }
        });

        const activeDroneIdx = (mode === '1st' && targetDrone) ? this.drones.indexOf(targetDrone) : -1;

        // Update waypoint marker visibility: disappear strictly when a drone is docked at the exact coordinate
        this.scene.traverse((obj) => {
            if (!obj.userData) return;
            const pt = obj.userData.point;
            let isOccupied = false;
            if (pt) {
                isOccupied = this.drones.some(d => d.currentPosition && d.currentPosition.distanceTo(pt) <= 0.05 * (d.scale || 1.0));
            }

            if (obj.userData.isMarkerBillboard) {
                obj.visible = (mode !== '1st') && !isOccupied;
            }
            if (obj.userData.isBeacon) {
                obj.visible = (mode === '1st' && obj.userData.droneIndex === activeDroneIdx) && !isOccupied;
            }
        });

        if (!this.hudOverlay) {
            this.hudOverlay = document.getElementById('hud-overlay');
            this.hudCenterCrosshair = document.getElementById('hud-center-crosshair');
            this.hudTarget = document.getElementById('hud-target');
            this.hudTargetText = document.getElementById('hud-target-text');
            this.hudArrivedMsg = document.getElementById('hud-arrived-msg');
        }

        if (mode !== '1st' && this.hudOverlay) {
            this.hudOverlay.style.display = 'none';
        }

        if (mode === 'free' || !targetDrone) {
            this.lastTrackedMode = 'free';
            return;
        }

        // Configure active drone for FPV cockpit view (arms & spinning rotors visible, core/sphere hidden)
        if (mode === '1st' && targetDrone.setFirstPersonMode) {
            targetDrone.setFirstPersonMode(true);
        }

        // Fallback direction heading vector if the drone is static or frozen
        let heading = targetDrone.mesh.rotation.z;
        let isMoving = targetDrone.currentVelocity.lengthSq() > 1e-4;
        if (isMoving) {
            heading = Math.atan2(targetDrone.currentVelocity.y, targetDrone.currentVelocity.x);
        }

        const isModeSwitch = (this.lastTrackedDrone !== targetDrone || this.lastTrackedMode !== mode);
        if (isModeSwitch) {
            this.trackedHeading = heading;
            this.lastTrackedDrone = targetDrone;
            this.lastTrackedMode = mode;
        }

        // Continuous shortest-path angular smoothing for both 1st and 3rd person cameras
        if (this.trackedHeading === null || Number.isNaN(this.trackedHeading)) {
            this.trackedHeading = heading;
        } else {
            let diff = (heading - this.trackedHeading) % (2 * Math.PI);
            if (diff < -Math.PI) diff += 2 * Math.PI;
            if (diff > Math.PI) diff -= 2 * Math.PI;
            
            // 0.055 provides a fluid gimbal-stabilized turn in FPV, 0.035 delivers smooth cinematic trailing in 3rd person
            const turnSmoothing = (mode === '1st') ? 0.055 : 0.035;
            this.trackedHeading += diff * turnSmoothing;
        }

        if (mode === '3rd') {
            const droneScale = targetDrone.scale || 1.0;
            // Vector parameters scaled proportionally to drone dimensions
            const offset = new THREE.Vector3(-8 * droneScale, 0, 4 * droneScale).applyAxisAngle(new THREE.Vector3(0, 0, 1), this.trackedHeading);
            const desiredPosition = new THREE.Vector3().copy(targetDrone.currentPosition).add(offset);
            
            if (isModeSwitch) {
                this.camera.position.copy(desiredPosition);
                this.controls.target.copy(targetDrone.currentPosition);
            } else {
                // Responsive spring-arm tracking across all scenario sizes
                this.camera.position.lerp(desiredPosition, 0.12);
                this.controls.target.lerp(targetDrone.currentPosition, 0.12);
            }
            this.controls.update();
        }
        else if (mode === '1st') {
            const smoothForward = new THREE.Vector3(Math.cos(this.trackedHeading), Math.sin(this.trackedHeading), 0);
            const droneScale = targetDrone.scale || 1.0;

            // Mount cockpit camera recessed and slightly elevated to frame both front rotors in the lower corners
            const setback = smoothForward.clone().multiplyScalar(-0.32 * droneScale);
            const elevation = new THREE.Vector3(0, 0, 0.16 * droneScale);
            const eyePos = new THREE.Vector3().copy(targetDrone.currentPosition).add(setback).add(elevation);
            this.camera.position.copy(eyePos);
            
            // Look ahead along the smoothly interpolated heading vector
            const lookTarget = new THREE.Vector3().copy(this.camera.position).add(smoothForward.multiplyScalar(10));
            if (isModeSwitch) {
                this.controls.target.copy(lookTarget);
            } else {
                this.controls.target.lerp(lookTarget, 0.15);
            }
            this.controls.update();

            // Update Tactical Screen-Space HUD Reticle
            if (this.hudOverlay) {
                this.hudOverlay.style.display = 'block';
                const cx = window.innerWidth / 2;
                const cy = window.innerHeight / 2;

                if (this.hudCenterCrosshair) {
                    this.hudCenterCrosshair.setAttribute('transform', `translate(${cx}, ${cy})`);
                }

                if (targetDrone.trajectory && targetDrone.trajectory.length > 0 && this.hudTarget && this.hudTargetText) {
                    const goalVec = targetDrone.targetGoal || new THREE.Vector3(
                        targetDrone.trajectory[targetDrone.trajectory.length - 1][0],
                        targetDrone.trajectory[targetDrone.trajectory.length - 1][1],
                        targetDrone.trajectory[targetDrone.trajectory.length - 1][2]
                    );
                    const droneDistToGoal = targetDrone.currentPosition.distanceTo(goalVec);
                    const toGoal = new THREE.Vector3().subVectors(goalVec, this.camera.position);
                    const cameraDistToGoal = toGoal.length();

                    const forward = new THREE.Vector3();
                    this.camera.getWorldDirection(forward);
                    const forwardDot = forward.dot(toGoal.clone().normalize());

                    // Check arrival based on the drone's actual coordinates and uncorrupted state
                    const isArrived = !targetDrone.isFailedState && (targetDrone.failureFrame === Infinity) && (droneDistToGoal <= 0.25 * (targetDrone.scale || 1.0));

                    if (this.hudArrivedMsg) {
                        this.hudArrivedMsg.style.display = isArrived ? 'block' : 'none';
                    }

                    // Project the true 3D goal position continuously without teleporting to screen center
                    if (!isArrived && forwardDot > 0.02) {
                        const proj = goalVec.clone().project(this.camera);
                        if (proj.z < 1.0 && Number.isFinite(proj.x) && Number.isFinite(proj.y)) {
                            const screenX = (proj.x * 0.5 + 0.5) * window.innerWidth;
                            const screenY = (-(proj.y * 0.5) + 0.5) * window.innerHeight;

                            this.hudTarget.setAttribute('transform', `translate(${screenX.toFixed(1)}, ${screenY.toFixed(1)})`);
                            this.hudTargetText.textContent = `G [${cameraDistToGoal.toFixed(1)}m]`;
                            this.hudTarget.style.display = 'block';
                        } else {
                            this.hudTarget.style.display = 'none';
                        }
                    } else {
                        this.hudTarget.style.display = 'none';
                    }
                }
            }
        }
    }

    loadDrones(trajectories, scaleMultiplier, sMinD, sMaxD, tMin, tMax, fMin, fMax, hMin, hMax) {
        this.clearDrones();
        const dronePaletteNum = [
            0x00ffcc, 0xff5555, 0xffbb00, 0xff00ff, 0x00ff66,
            0x5599ff, 0xff8800, 0xcc66ff, 0xffff00, 0x00bcd4
        ];

        trajectories.forEach((item, index) => {
            const colorIdx = item.colorIndex !== undefined ? item.colorIndex : index;
            const assignedColor = dronePaletteNum[colorIdx % dronePaletteNum.length];
            const droneId = item.id !== undefined ? item.id : (colorIdx + 1);
            const droneName = item.name || `Drone ${droneId}`;
            const failFrame = (item.failure_frame !== undefined) ? item.failure_frame : null;
            const targetStart = item.target_start || (item.path ? item.path[0] : null);
            const targetGoal = item.target_goal || (item.path ? item.path[item.path.length - 1] : null);

            // item is {solver: "...", path: [...], failure_frame: ..., target_start: ..., target_goal: ...}
            this.drones.push(new DroneEntity(
                this.scene, item.path, scaleMultiplier, droneId, 
                tMin, tMax, fMin, fMax, hMin, hMax, sMinD, sMaxD, item.solver, assignedColor, droneName, failFrame,
                targetStart, targetGoal
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
        this.defaultCameraPos = position.clone();
        this.defaultCameraTarget = target.clone();
        this.defaultZoom = zoom;

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

    setNameplatesVisible(visible) {
        this.nameplatesVisible = visible;
        this.drones.forEach(d => {
            if (d.nameTag) {
                if (!visible || this.lastTrackedMode === '1st') {
                    d.nameTag.visible = false;
                } else if (this.lastTrackedMode === '3rd') {
                    d.nameTag.visible = (d === this.lastTrackedDrone);
                } else {
                    d.nameTag.visible = true;
                }
            }
        });
    }

    render() {
        this.controls.update();
        this.renderer.render(this.scene, this.camera);
    }
}