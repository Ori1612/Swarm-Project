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
            this.updateSolverOptions(e.target.value);
            this.loadScenario(e.target.value);
        });

        document.getElementById('cam-free').addEventListener('click', () => {
            this.cameraMode = 'free';
            this.sceneManager.controls.enabled = true;
            this.update();
        });
        document.getElementById('cam-3rd').addEventListener('click', () => {
            this.cameraMode = '3rd';
            this.sceneManager.controls.enabled = false;
            this.update();
        });
        document.getElementById('cam-1st').addEventListener('click', () => {
            this.cameraMode = '1st';
            this.sceneManager.controls.enabled = false;
            this.update();
        });

        const mathBtn = document.getElementById('math-mode-btn');
        mathBtn.addEventListener('click', () => {
            this.mathMode = !this.mathMode;
            mathBtn.innerText = `Toggle Math Mode (${this.mathMode ? 'On' : 'Off'})`;
            if (!this.mathMode) this.envBuilder.clearKKTPlanes();
        });

        document.getElementById('merge-times').addEventListener('change', (e) => {
            document.getElementById('cbs-slider-area').style.display = e.target.checked ? 'none' : 'block';
            this.applySliderMode();
            this.update();
        });

        document.getElementById('solver-select').addEventListener('change', (e) => {
            const isBoth = e.target.value === 'both';
            const mergeCheck = document.getElementById('merge-times');
            document.getElementById('merge-container').style.display = isBoth ? 'flex' : 'none';
            
            document.getElementById('cbs-slider-area').style.display = (isBoth && !mergeCheck.checked) ? 'block' : 'none';
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
        
        this.updateSolverOptions(document.getElementById('scenario-select').value);
    }

    updateSolverOptions(scenarioId) {
        const select = document.getElementById('solver-select');
        const currentVal = select.value;
        select.innerHTML = '';
        let options = [];
        
        if (scenarioId === 'torture_track') {
            options = [{val: 'both', text: 'Both'}, {val: 'scp', text: 'SCP Only'}, {val: 'cbs', text: 'CBS Only'}];
        } else if (scenarioId.startsWith('stress_phase1')) {
            options = [{val: 'apf', text: 'APF'}, {val: 'sa', text: 'SA'}, {val: 'scp', text: 'SCP'}];
        } else if (scenarioId === 'csg_maze') {
            options = [{val: 'sa', text: 'SA'}, {val: 'scp', text: 'SCP'}];
        } else {
            options = [{val: 'scp', text: 'SCP'}];
        }
        
        options.forEach(o => {
            const opt = document.createElement('option');
            opt.value = o.val;
            opt.innerText = o.text;
            select.appendChild(opt);
        });
        
        if (options.some(o => o.val === currentVal)) select.value = currentVal;
        else select.value = options[0].val;
        
        document.getElementById('merge-container').style.display = select.value === 'both' ? 'flex' : 'none';
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
                minD: 5, maxD: 200, scaleMinD: 100, scaleMaxD: 200, 
                tagMin: 8, tagMax: 18, fontMin: 28, fontMax: 28,
                tagScale: 1.0, heightMin: 5, heightMax: 8, totalT: 75,
                cameraPos: new THREE.Vector3(50, 200, 175),
                cameraTarget: new THREE.Vector3(50, 50, 50), zoom: 200
            },
            'torture_track': {
                minD: 1, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 1.25, heightMax: 2, totalT: 20,
                cameraPos: new THREE.Vector3(30, 30, 30),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
            },
            'csg_maze': {
                minD: 1, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 1.25, heightMax: 2, totalT: 30,
                cameraPos: new THREE.Vector3(35, 10, 40),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
            },
            'stress_phase1_k0': {
                minD: 1, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 1.25, heightMax: 2, totalT: 30,
                cameraPos: new THREE.Vector3(-20, 10, 35),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
            },
            'stress_phase1_k2': {
                minD: 1, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 1.25, heightMax: 2, totalT: 30,
                cameraPos: new THREE.Vector3(-20, 10, 35),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
            },
            'stress_phase1_k4': {
                minD: 1, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 1.25, heightMax: 2, totalT: 30,
                cameraPos: new THREE.Vector3(-20, 10, 35),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
            },
            'stress_phase1_k6': {
                minD: 1, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 1.25, heightMax: 2, totalT: 30,
                cameraPos: new THREE.Vector3(-20, 10, 35),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
            },
            'stress_phase1_k8': {
                minD: 1, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 2, tagMax: 4, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 1.25, heightMax: 2, totalT: 30,
                cameraPos: new THREE.Vector3(-20, 10, 35),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
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
        
        // --- FIXED: Calculate scale multiplier BEFORE using it ---
        const envSize = data.bounds ? Math.max(data.bounds[1][0], data.bounds[1][1], data.bounds[1][2]) : 20;
        const scaleMultiplier = envSize / 20;

        if (data.trajectories && data.trajectories.length > 0) {
            // Priority: If the backend sends 'control_points', use them for the markers.
            // Otherwise, fallback to the trajectory endpoints.
            const markerData = data.control_points || data.trajectories.map(item => ({
                start: item.path ? item.path[0] : item[0],
                goal: item.path ? item.path[item.path.length - 1] : item[item.length - 1]
            }));
            
            if (!this.envBuilder.markers) this.envBuilder.markers = [];
            this.envBuilder.renderMarkers(markerData, scaleMultiplier, config.tagScale || 1.0);
        }

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

        // --- FIXED: Initialize grid and camera AFTER all geometry is built ---
        if (data.bounds) this.sceneManager.frameBounds(data.bounds[0], data.bounds[1]);
        
        // Apply custom camera view if defined in the profile
        if (config.cameraPos && config.cameraTarget) {
            this.sceneManager.hasCustomCameraView = true; // Flag to prevent frameBounds override
            this.sceneManager.setCameraView(config.cameraPos, config.cameraTarget, config.zoom);
        } else {
            this.sceneManager.hasCustomCameraView = false;
        }

        // Setup Array Length Boundaries
        this.scpMax = (data.trajectories && data.trajectories.length > 0 && data.trajectories[0].path) ? data.trajectories[0].path.length - 1 : (data.dynamic_T - 1);
        this.cbsMax = this.scpMax;
        
        if (data.trajectories && data.trajectories.length > 1) {
            const cbsTraj = data.trajectories.find(t => t.solver.toUpperCase() === 'CBS');
            if (cbsTraj && cbsTraj.path) this.cbsMax = cbsTraj.path.length - 1;
        }
        
        this.timeSlider.value = 0;
        const cbsSlider = document.getElementById('cbs-time-slider');
        if (cbsSlider) {
            cbsSlider.value = 0;
            document.getElementById('cbs-time-val').innerText = '0.0';
        }
        
        this.applySliderMode();
    }

    applySliderMode() {
        // Enforce percentage bounds globally across all evaluation configurations
        document.getElementById('time-label-text').innerText = 'Progress:';
        this.timeSlider.max = 100;
        
        const cbsSlider = document.getElementById('cbs-time-slider');
        if (cbsSlider) cbsSlider.max = 100;
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
        const isBoth = document.getElementById('solver-select').value === 'both';
        const sliderVal = parseFloat(this.timeSlider.value);
        
        this.timeVal.innerText = sliderVal.toFixed(1) + '%';
        const scpTime = (sliderVal / 100) * this.scpMax;

        if (!isBoth || mergeCheck.checked) {
            const cbsTime = (sliderVal / 100) * this.cbsMax;
            this.sceneManager.updateDrones(isBoth ? [scpTime, cbsTime] : scpTime);
            
            const cbsTimeVal = document.getElementById('cbs-time-val');
            if (cbsTimeVal) cbsTimeVal.innerText = sliderVal.toFixed(1) + '%';
            const cbsSlider = document.getElementById('cbs-time-slider');
            if (cbsSlider) cbsSlider.value = sliderVal;
        } else {
            const cbsSlider = document.getElementById('cbs-time-slider');
            const cbsVal = cbsSlider ? parseFloat(cbsSlider.value) : sliderVal;
            
            const cbsTimeVal = document.getElementById('cbs-time-val');
            if (cbsTimeVal) cbsTimeVal.innerText = cbsVal.toFixed(1) + '%';
            
            const cbsTime = (cbsVal / 100) * this.cbsMax;
            this.sceneManager.updateDrones([scpTime, cbsTime]);
        }

        const targetDrone = this.sceneManager.getDrone(this.targetDroneIdx);
        if (targetDrone) {
            this.sceneManager.updateCameraTracking(targetDrone, this.cameraMode);
        }
    }
}