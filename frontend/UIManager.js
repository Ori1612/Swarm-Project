import * as THREE from 'three';

export class UIManager {
    constructor(sceneManager, envBuilder, apiService) {
        this.sceneManager = sceneManager;
        this.envBuilder = envBuilder;
        this.api = apiService;
        this.cameraMode = 'free';
        this.targetDroneIdx = 0;
        this.mathMode = false;

        this.timeSlider = document.getElementById('time-slider');
        this.timeVal = document.getElementById('time-val');

        this.bindEvents();
    }

    bindEvents() {
        document.getElementById('scenario-select').addEventListener('change', (e) => {
            const isGapTest = e.target.value === 'torture_track';
            document.getElementById('gap-test-controls').style.display = isGapTest ? 'block' : 'none';
            this.loadScenario(e.target.value);
        });

        document.getElementById('cam-free').addEventListener('click', () => {
            this.cameraMode = 'free';
            this.sceneManager.controls.enabled = true;
        });
        document.getElementById('cam-3rd').addEventListener('click', () => {
            this.cameraMode = '3rd';
            this.sceneManager.controls.enabled = false;
        });
        document.getElementById('cam-1st').addEventListener('click', () => {
            this.cameraMode = '1st';
            this.sceneManager.controls.enabled = false;
        });

        const mathBtn = document.getElementById('math-mode-btn');
        mathBtn.addEventListener('click', () => {
            this.mathMode = !this.mathMode;
            mathBtn.innerText = `Toggle Math Mode (${this.mathMode ? 'On' : 'Off'})`;
            if (!this.mathMode) this.envBuilder.clearKKTPlanes();
        });

        document.getElementById('merge-times').addEventListener('change', (e) => {
            document.getElementById('cbs-slider-area').style.display = e.target.checked ? 'none' : 'block';
        });

        document.getElementById('solver-select').addEventListener('change', (e) => {
            const isBoth = e.target.value === 'both';
            document.getElementById('merge-container').style.display = isBoth ? 'block' : 'none';
            // If we are not in 'both' mode, ensure the CBS slider is also hidden
            if (!isBoth) document.getElementById('cbs-slider-area').style.display = 'none';
            this.loadScenario(document.getElementById('scenario-select').value);
        });

        document.getElementById('cbs-time-slider').addEventListener('input', () => this.update());

        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        window.addEventListener('click', (event) => {
            const droneMeshes = this.sceneManager.getDroneMeshes();
            if (!this.mathMode || droneMeshes.length === 0) return;
            mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
            mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
            raycaster.setFromCamera(mouse, this.sceneManager.camera);
            const hits = raycaster.intersectObjects(droneMeshes);
            if (hits.length > 0) this.triggerKKTQuery(hits[0].object.position);
        });
    }

    async loadScenario(id) {
        const mode = document.getElementById('solver-select').value;
        const data = await this.api.fetchScenario(id, mode);
        if (!data || data.error) { 
            console.error('Backend error:', data ? data.error : 'Unknown error'); 
            return; 
        }

        // --- TUNING PANEL: Configure limits for each scenario group ---
        // 1. "cyber_city" (Large Environment)
        // 2. "others" (Torture Track, CSG Maze, Stress Tests)
        // Define specific camera views for each environment
        const profiles = {
            'cyber_city': { 
                minD: 5, maxD: 200, 
                scaleMinD: 100, scaleMaxD: 200, 
                tagMin: 8, tagMax: 18, 
                fontMin: 28, fontMax: 28,
                heightMin: 5, heightMax: 8,
                cameraPos: new THREE.Vector3(50, 200, 175),
                cameraTarget: new THREE.Vector3(50, 50, 50),
                zoom: 200
            },
            'torture_track': {
                minD: 1, maxD: 40, 
                scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, 
                fontMin: 28, fontMax: 28,
                heightMin: 1.25, heightMax: 2,
                cameraPos: new THREE.Vector3(30, 30, 30),
                cameraTarget: new THREE.Vector3(10, 10, 10),
                zoom: 40
            },
            'csg_maze': {
                minD: 1, maxD: 40, 
                scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, 
                fontMin: 28, fontMax: 28,
                heightMin: 1.25, heightMax: 2,
                cameraPos: new THREE.Vector3(35, 10, 40),
                cameraTarget: new THREE.Vector3(10, 10, 10),
                zoom: 40
            },
            'stress_phase1_k0': {
                minD: 1, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, fontMin: 28, fontMax: 28,
                heightMin: 1.25, heightMax: 2,
                cameraPos: new THREE.Vector3(35, 35, 30),
                cameraTarget: new THREE.Vector3(10, 10, 10),
                zoom: 40
            },
            'stress_phase1_k2': {
                minD: 1, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, fontMin: 28, fontMax: 28,
                heightMin: 1.25, heightMax: 2,
                cameraPos: new THREE.Vector3(30, 30, 35),
                cameraTarget: new THREE.Vector3(10, 10, 10),
                zoom: 40
            },
            'stress_phase1_k4': {
                minD: 1, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, fontMin: 28, fontMax: 28,
                heightMin: 1.25, heightMax: 2,
                cameraPos: new THREE.Vector3(10, -15, 30),
                cameraTarget: new THREE.Vector3(10, 10, 10),
                zoom: 40
            },
            'stress_phase1_k6': {
                minD: 1, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, fontMin: 28, fontMax: 28,
                heightMin: 1.25, heightMax: 2,
                cameraPos: new THREE.Vector3(-25, 10, 30),
                cameraTarget: new THREE.Vector3(10, 10, 10),
                zoom: 40
            },
            'stress_phase1_k8': {
                minD: 1, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, fontMin: 28, fontMax: 28,
                heightMin: 1.25, heightMax: 2,
                cameraPos: new THREE.Vector3(-20, 10, 35),
                cameraTarget: new THREE.Vector3(10, 10, 10),
                zoom: 40
            }
        };
        
        // Direct lookup; fallback to csg_maze if the scenario is unknown
        let config = profiles[id] || profiles['csg_maze'];

        // Developer Tool: Log camera state with 'L' key
        window.addEventListener('keydown', (e) => {
            if (e.key === 'l' || e.key === 'L') {
                const pos = this.sceneManager.camera.position;
                const target = this.sceneManager.controls.target;
                const dist = this.sceneManager.controls.getDistance();
                console.log(`--- Camera Debug ---`);
                console.log(`cameraPos: new THREE.Vector3(${pos.x.toFixed(1)}, ${pos.y.toFixed(1)}, ${pos.z.toFixed(1)}),`);
                console.log(`cameraTarget: new THREE.Vector3(${target.x.toFixed(1)}, ${target.y.toFixed(1)}, ${target.z.toFixed(1)}),`);
                console.log(`zoom: ${dist.toFixed(1)}`);
            }
        });

        this.envBuilder.teardown();
        this.envBuilder.build(data.obstacles);
        
        const envSize = data.bounds ? Math.max(data.bounds[1][0], data.bounds[1][1], data.bounds[1][2]) : 20;
        const scaleMultiplier = envSize / 20;

        // 1. Update Camera Limits
        this.sceneManager.updateCameraLimits(config.minD, config.maxD);

        // 2. Load Drones with Profile
        this.sceneManager.loadDrones(
            data.trajectories, 
            scaleMultiplier, 
            config.scaleMinD, config.scaleMaxD, 
            config.tagMin, config.tagMax, 
            config.fontMin, config.fontMax,
            config.heightMin, config.heightMax
        );

        if (data.bounds) this.sceneManager.frameBounds(data.bounds[0], data.bounds[1]);
        
        // Apply custom camera view if defined in the profile
        if (config.cameraPos && config.cameraTarget) {
            this.sceneManager.setCameraView(config.cameraPos, config.cameraTarget, config.zoom);
        }

        if (data.trajectories.length > 0) {
            this.timeSlider.max = data.trajectories[0].length - 1;
        }
        this.timeSlider.value = 0;
    }

    async triggerKKTQuery(pointVec) {
        const tInt = Math.floor(parseFloat(this.timeSlider.value));
        const data = await this.api.fetchKKTQuery(pointVec, tInt);
        
        if (!data) return;
        
        this.envBuilder.clearKKTPlanes();
        (data.hyperplanes || []).forEach(hp => {
            const normal = hp.gradient || hp.normal_vector || hp.normal || hp;
            this.envBuilder.renderKKTPlane(
                [pointVec.x, pointVec.y, pointVec.z], normal
            );
        });
    }

    update() {
        const mergeCheck = document.getElementById('merge-times');
        const scpTime = parseFloat(this.timeSlider.value);
        this.timeVal.innerText = scpTime.toFixed(1);

        if (mergeCheck.checked) {
            this.sceneManager.updateDrones(scpTime);
        } else {
            const cbsSlider = document.getElementById('cbs-time-slider');
            const cbsTime = cbsSlider ? parseFloat(cbsSlider.value) : scpTime;
            document.getElementById('cbs-time-val').innerText = cbsTime.toFixed(1);
            this.sceneManager.updateDrones([scpTime, cbsTime]);
        }

        const targetDrone = this.sceneManager.getDrone(this.targetDroneIdx);
        if (targetDrone) {
            this.sceneManager.updateCameraTracking(targetDrone, this.cameraMode);
        }
    }
}