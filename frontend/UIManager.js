import * as THREE from 'three';

export class UIManager {
    constructor(sceneManager, envBuilder, apiService) {
        this.sceneManager = sceneManager;
        this.envBuilder = envBuilder;
        this.api = apiService;
        this.cameraMode = 'free';
        this.targetDroneIdx = 0;
        this.nameplatesEnabled = true;

        this.timeSlider = document.getElementById('time-slider');
        this.timeVal = document.getElementById('time-val');
        this.isPlaying = false;
        this.isLooping = false;
        this.playbackSpeed = 1.0;
        this.playbackProgress = 0.0;
        this.lastTime = performance.now();

        this.bindEvents();
    }

    bindEvents() {
        const uiContainer = document.getElementById('ui-container');
        const miniUiContainer = document.getElementById('mini-ui-container');
        const toggleUiBtn = document.getElementById('toggle-ui-btn');
        const miniToggleUiBtn = document.getElementById('mini-toggle-ui-btn');

        if (toggleUiBtn && uiContainer && miniUiContainer) {
            toggleUiBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                uiContainer.style.display = 'none';
                miniUiContainer.style.display = 'flex';
            });
        }

        if (miniToggleUiBtn && uiContainer && miniUiContainer) {
            miniToggleUiBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                miniUiContainer.style.display = 'none';
                uiContainer.style.display = 'block';
            });
        }

        document.getElementById('scenario-select').addEventListener('change', (e) => {
            localStorage.setItem('swarm_selected_scenario', e.target.value);
            this.updateSolverOptions(e.target.value);
            localStorage.setItem('swarm_selected_solver', document.getElementById('solver-select').value);
            this.loadScenario(e.target.value);
        });

        const sphereOpacitySlider = document.getElementById('sphere-opacity-slider');
        if (sphereOpacitySlider) {
            sphereOpacitySlider.addEventListener('input', (e) => {
                const val = parseFloat(e.target.value);
                const valDisplay = document.getElementById('sphere-opacity-val');
                if (valDisplay) valDisplay.innerText = val.toFixed(2);
                if (this.sceneManager && this.sceneManager.drones) {
                    this.sceneManager.drones.forEach(drone => {
                        if (drone.setSphereOpacity) drone.setSphereOpacity(val);
                    });
                }
            });
        }

        document.getElementById('cam-3rd').addEventListener('click', () => {
            if (this.cameraMode === '3rd') {
                this.cameraMode = 'free';
                this.sceneManager.controls.enabled = true;
                if (this.currentConfig && this.currentConfig.cameraPos && this.currentConfig.cameraTarget) {
                    this.sceneManager.setCameraView(this.currentConfig.cameraPos, this.currentConfig.cameraTarget, this.currentConfig.zoom);
                }
            } else {
                this.cameraMode = '3rd';
                this.sceneManager.controls.enabled = false;
            }
            this.updateCameraButtonStyles();
            this.update();
        });
        document.getElementById('cam-1st').addEventListener('click', () => {
            if (this.cameraMode === '1st') {
                this.cameraMode = 'free';
                this.sceneManager.controls.enabled = true;
                if (this.currentConfig && this.currentConfig.cameraPos && this.currentConfig.cameraTarget) {
                    this.sceneManager.setCameraView(this.currentConfig.cameraPos, this.currentConfig.cameraTarget, this.currentConfig.zoom);
                }
            } else {
                this.cameraMode = '1st';
                this.sceneManager.controls.enabled = false;
            }
            this.updateCameraButtonStyles();
            this.update();
        });

        const droneTargetSelect = document.getElementById('drone-target-select');
        if (droneTargetSelect) {
            droneTargetSelect.addEventListener('change', (e) => {
                this.targetDroneIdx = parseInt(e.target.value, 10) || 0;
                this.update();
            });
        }

        if (this.timeSlider) {
            this.timeSlider.addEventListener('input', () => {
                this.playbackProgress = parseFloat(this.timeSlider.value) || 0;
                this.update();
            });
        }

        const playBtn = document.getElementById('play-btn');
        const miniPlayBtn = document.getElementById('mini-play-btn');
        if (playBtn) playBtn.addEventListener('click', () => this.togglePlay());
        if (miniPlayBtn) miniPlayBtn.addEventListener('click', () => this.togglePlay());

        const loopBtn = document.getElementById('loop-btn');
        const miniLoopBtn = document.getElementById('mini-loop-btn');
        const toggleLoop = () => {
            this.isLooping = !this.isLooping;
            if (loopBtn) loopBtn.classList.toggle('active', this.isLooping);
            if (miniLoopBtn) miniLoopBtn.classList.toggle('active', this.isLooping);
        };
        if (loopBtn) loopBtn.addEventListener('click', toggleLoop);
        if (miniLoopBtn) miniLoopBtn.addEventListener('click', toggleLoop);

        const speedSelect = document.getElementById('speed-select');
        const miniSpeedSelect = document.getElementById('mini-speed-select');
        const updateSpeed = (val) => {
            this.playbackSpeed = parseFloat(val) || 1.0;
            if (speedSelect) speedSelect.value = val;
            if (miniSpeedSelect) miniSpeedSelect.value = val;
        };
        if (speedSelect) speedSelect.addEventListener('change', (e) => updateSpeed(e.target.value));
        if (miniSpeedSelect) miniSpeedSelect.addEventListener('change', (e) => updateSpeed(e.target.value));

        const nameplatesBtn = document.getElementById('nameplates-btn');
        const miniNameplatesBtn = document.getElementById('mini-nameplates-btn');
        const toggleNameplates = (e) => {
            if (e) e.stopPropagation();
            this.nameplatesEnabled = !this.nameplatesEnabled;
            if (nameplatesBtn) nameplatesBtn.classList.toggle('active', this.nameplatesEnabled);
            if (miniNameplatesBtn) miniNameplatesBtn.classList.toggle('active', this.nameplatesEnabled);
            this.sceneManager.setNameplatesVisible(this.nameplatesEnabled);
        };
        if (nameplatesBtn) nameplatesBtn.addEventListener('click', toggleNameplates);
        if (miniNameplatesBtn) miniNameplatesBtn.addEventListener('click', toggleNameplates);

        document.getElementById('merge-times').addEventListener('change', (e) => {
            document.getElementById('cbs-slider-area').style.display = e.target.checked ? 'none' : 'block';
            this.applySliderMode();
            this.updatePlayControlsState();
            this.update();
        });

        document.getElementById('solver-select').addEventListener('change', (e) => {
            localStorage.setItem('swarm_selected_solver', e.target.value);
            const isBoth = e.target.value === 'both';
            const mergeCheck = document.getElementById('merge-times');
            document.getElementById('merge-container').style.display = isBoth ? 'flex' : 'none';
            
            document.getElementById('cbs-slider-area').style.display = (isBoth && !mergeCheck.checked) ? 'block' : 'none';
            this.updatePlayControlsState();
            this.loadScenario(document.getElementById('scenario-select').value);
        });

        document.getElementById('cbs-time-slider').addEventListener('input', () => this.update());
        
        // Restore active scenario and solver state across browser refreshes
        const savedScenario = localStorage.getItem('swarm_selected_scenario');
        const scenarioSelect = document.getElementById('scenario-select');
        if (savedScenario && Array.from(scenarioSelect.options).some(o => o.value === savedScenario)) {
            scenarioSelect.value = savedScenario;
        }

        this.updateSolverOptions(scenarioSelect.value);

        const savedSolver = localStorage.getItem('swarm_selected_solver');
        const solverSelect = document.getElementById('solver-select');
        if (savedSolver && Array.from(solverSelect.options).some(o => o.value === savedSolver)) {
            solverSelect.value = savedSolver;
        }
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
        this.applySliderMode();
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
                tagMin: 12, tagMax: 20, fontMin: 28, fontMax: 28,
                tagScale: 1.0, heightMin: 8, heightMax: 12, totalT: 75,
                cameraPos: new THREE.Vector3(50, 200, 175),
                cameraTarget: new THREE.Vector3(50, 50, 50), zoom: 200
            },
            'torture_track': {
                minD: 1.25, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 3, tagMax: 5, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 2, heightMax: 3, totalT: 20,
                cameraPos: new THREE.Vector3(30, 30, 30),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
            },
            'csg_maze': {
                minD: 1.25, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 3, tagMax: 5, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 2, heightMax: 3, totalT: 30,
                cameraPos: new THREE.Vector3(35, 10, 40),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
            },
            'stress_phase1_k0': {
                minD: 1.25, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 3, tagMax: 5, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 2, heightMax: 3, totalT: 30,
                cameraPos: new THREE.Vector3(-20, 10, 35),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
            },
            'stress_phase1_k2': {
                minD: 1.25, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 3, tagMax: 5, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 2, heightMax: 3, totalT: 30,
                cameraPos: new THREE.Vector3(-20, 10, 35),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
            },
            'stress_phase1_k4': {
                minD: 1.25, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 3, tagMax: 5, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 2, heightMax: 3, totalT: 30,
                cameraPos: new THREE.Vector3(-20, 10, 35),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
            },
            'stress_phase1_k6': {
                minD: 1.25, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 3, tagMax: 5, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 2, heightMax: 3, totalT: 30,
                cameraPos: new THREE.Vector3(-20, 10, 35),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
            },
            'stress_phase1_k8': {
                minD: 1.25, maxD: 40, scaleMinD: 20, scaleMaxD: 40, 
                tagMin: 3, tagMax: 5, fontMin: 28, fontMax: 28,
                tagScale: 0.5, heightMin: 2, heightMax: 3, totalT: 30,
                cameraPos: new THREE.Vector3(-20, 10, 35),
                cameraTarget: new THREE.Vector3(10, 10, 10), zoom: 40
            }
        };
        
        // Direct lookup; fallback to csg_maze if the scenario is unknown
        let config = profiles[id] || profiles['csg_maze'];
        this.currentConfig = config;
        this.cameraMode = 'free';
        this.sceneManager.controls.enabled = true;
        this.updateCameraButtonStyles();

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
        
        // Dynamic Drone Radius transmitted directly from backend Single Source of Truth
        const physicalDroneRadius = (data.drone_radius !== undefined) ? data.drone_radius : (id === 'cyber_city' ? 2.0 : 0.5);

        // Tag trajectories with persistent solver color mappings (CBS is strictly Red = 1, SCP is Cyan = 0)
        const allTrajectories = (data.trajectories || []).map((t, idx) => {
            const isCBS = t.solver && t.solver.toUpperCase() === 'CBS';
            const colorIdx = isCBS ? 1 : (t.colorIndex !== undefined ? t.colorIndex : idx);
            const droneId = isCBS ? 2 : (t.id !== undefined ? t.id : idx + 1);
            return {
                ...t,
                colorIndex: colorIdx,
                id: droneId,
                name: (id === 'torture_track' && t.solver) ? t.solver.toUpperCase() : `Drone ${droneId}`
            };
        });

        // Filter trajectories according to the selected solver mode (SCP, CBS, or Both)
        const activeTrajectories = (allTrajectories && mode && mode !== 'both')
            ? allTrajectories.filter(t => !t.solver || t.solver.toLowerCase() === mode.toLowerCase())
            : allTrajectories;

        const trajectoriesToLoad = (activeTrajectories.length > 0) ? activeTrajectories : allTrajectories;

        // Populate target drone selection dropdown for 1st & 3rd person tracking
        const droneTargetSelect = document.getElementById('drone-target-select');
        if (droneTargetSelect) {
            droneTargetSelect.innerHTML = '';
            trajectoriesToLoad.forEach((t, idx) => {
                const opt = document.createElement('option');
                opt.value = idx;
                opt.innerText = t.name || `Drone ${t.id || idx + 1}`;
                droneTargetSelect.appendChild(opt);
            });
            if (this.targetDroneIdx >= trajectoriesToLoad.length) {
                this.targetDroneIdx = 0;
            }
            droneTargetSelect.value = this.targetDroneIdx;
        }

        if (trajectoriesToLoad && trajectoriesToLoad.length > 0) {
            let markerData = [];
            if (id === 'torture_track') {
                markerData = trajectoriesToLoad.map(item => {
                    const isCBS = item.solver && item.solver.toUpperCase() === 'CBS';
                    return {
                        start: item.path ? item.path[0] : item[0],
                        goal: item.path ? item.path[item.path.length - 1] : item[item.length - 1],
                        colorIndex: isCBS ? 1 : 0
                    };
                });
            } else if (data.control_points && data.control_points.length > 0) {
                markerData = data.control_points.map((cp, idx) => ({
                    start: cp.start,
                    goal: cp.goal,
                    colorIndex: cp.colorIndex !== undefined ? cp.colorIndex : idx
                }));
            } else {
                markerData = trajectoriesToLoad.map(item => ({
                    start: item.path ? item.path[0] : item[0],
                    goal: item.path ? item.path[item.path.length - 1] : item[item.length - 1],
                    colorIndex: item.colorIndex !== undefined ? item.colorIndex : 0
                }));
            }
            
            if (!this.envBuilder.markers) this.envBuilder.markers = [];
            this.envBuilder.renderMarkers(markerData, physicalDroneRadius, config.tagScale || 1.0);
        }

        // 1. Update Camera Limits
        this.sceneManager.updateCameraLimits(config.minD, config.maxD);

        // 2. Load Drones with Profile (Exact 1:1 physical collision hull)
        this.sceneManager.loadDrones(
            trajectoriesToLoad, 
            physicalDroneRadius, 
            config.scaleMinD, config.scaleMaxD, 
            config.tagMin, config.tagMax, 
            config.fontMin, config.fontMax,
            config.heightMin, config.heightMax
        );

        // Persist user-selected sphere opacity across scenario changes
        const sphereOpacitySlider = document.getElementById('sphere-opacity-slider');
        if (sphereOpacitySlider && this.sceneManager.drones) {
            const currentOpacity = parseFloat(sphereOpacitySlider.value);
            this.sceneManager.drones.forEach(drone => {
                if (drone.setSphereOpacity) drone.setSphereOpacity(currentOpacity);
            });
        }

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
        this.scpMax = (trajectoriesToLoad && trajectoriesToLoad.length > 0 && trajectoriesToLoad[0].path) ? trajectoriesToLoad[0].path.length - 1 : (data.dynamic_T - 1);
        this.cbsMax = this.scpMax;
        
        if (trajectoriesToLoad && trajectoriesToLoad.length > 1) {
            const cbsTraj = trajectoriesToLoad.find(t => t.solver && t.solver.toUpperCase() === 'CBS');
            if (cbsTraj && cbsTraj.path) this.cbsMax = cbsTraj.path.length - 1;
        }
        
        this.isPlaying = false;
        this.playbackProgress = 0.0;
        this.updatePlayButton();
        this.updatePlayControlsState();

        this.timeSlider.value = 0;
        const cbsSlider = document.getElementById('cbs-time-slider');
        if (cbsSlider) {
            cbsSlider.value = 0;
            document.getElementById('cbs-time-val').innerText = '0.0';
        }
        
        this.applySliderMode();
    }

    applySliderMode() {
        const isBoth = document.getElementById('solver-select').value === 'both';
        const mergeCheck = document.getElementById('merge-times');
        const isUnmergedBoth = isBoth && mergeCheck && !mergeCheck.checked;

        const timeLabel = document.getElementById('time-label-text');
        if (timeLabel) {
            timeLabel.innerText = isUnmergedBoth ? 'SCP Progress:' : 'Progress:';
        }

        const cbsLabel = document.getElementById('cbs-label-text');
        if (cbsLabel) {
            cbsLabel.innerText = 'CBS Progress:';
        }

        // Enforce percentage bounds globally across all evaluation configurations
        this.timeSlider.max = 100;
        
        const cbsSlider = document.getElementById('cbs-time-slider');
        if (cbsSlider) cbsSlider.max = 100;
    }

    updatePlayControlsState() {
        const isBoth = document.getElementById('solver-select').value === 'both';
        const mergeCheck = document.getElementById('merge-times');
        const isMerged = !isBoth || (mergeCheck && mergeCheck.checked);

        const playBtn = document.getElementById('play-btn');
        const miniPlayBtn = document.getElementById('mini-play-btn');
        const loopBtn = document.getElementById('loop-btn');
        const miniLoopBtn = document.getElementById('mini-loop-btn');
        const speedSelect = document.getElementById('speed-select');
        const miniSpeedSelect = document.getElementById('mini-speed-select');

        const disable = !isMerged;
        [playBtn, miniPlayBtn, loopBtn, miniLoopBtn, speedSelect, miniSpeedSelect].forEach(el => {
            if (el) el.disabled = disable;
        });

        if (disable && this.isPlaying) {
            this.isPlaying = false;
            this.updatePlayButton();
        }
    }

    updateCameraButtonStyles() {
        const btn3rd = document.getElementById('cam-3rd');
        const btn1st = document.getElementById('cam-1st');
        if (!btn3rd || !btn1st) return;

        btn3rd.classList.toggle('active', this.cameraMode === '3rd');
        btn1st.classList.toggle('active', this.cameraMode === '1st');
    }

    togglePlay() {
        this.isPlaying = !this.isPlaying;
        if (this.isPlaying) {
            this.playbackProgress = parseFloat(this.timeSlider.value) || 0;
            if (this.playbackProgress >= 100) {
                this.playbackProgress = 0;
                this.timeSlider.value = '0';
            }
            this.lastTime = performance.now();
        }
        this.updatePlayButton();
    }

    updatePlayButton() {
        const playBtn = document.getElementById('play-btn');
        const miniPlayBtn = document.getElementById('mini-play-btn');
        const iconHtml = this.isPlaying
            ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="3" width="5.5" height="18" rx="1"/><rect x="14.5" y="3" width="5.5" height="18" rx="1"/></svg>'
            : '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>';

        if (playBtn) {
            playBtn.innerHTML = iconHtml;
            playBtn.classList.toggle('active', this.isPlaying);
        }
        if (miniPlayBtn) {
            miniPlayBtn.innerHTML = iconHtml;
            miniPlayBtn.classList.toggle('active', this.isPlaying);
        }
    }

    update() {
        const now = performance.now();
        const dt = Math.min((now - (this.lastTime || now)) / 1000, 0.1);
        this.lastTime = now;

        if (this.isPlaying) {
            // Base rate: 10% progress per second (0% to 100% in 10 seconds at 1.0x)
            const baseRate = 10;
            this.playbackProgress += baseRate * this.playbackSpeed * dt;
            if (this.playbackProgress >= 100) {
                if (this.isLooping) {
                    this.playbackProgress = this.playbackProgress % 100;
                } else {
                    this.playbackProgress = 100;
                    this.isPlaying = false;
                    this.updatePlayButton();
                }
            }
            this.timeSlider.value = this.playbackProgress.toFixed(2);
        }

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