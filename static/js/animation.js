class NexusAnimation {
    constructor() {
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.mouse = { x: -100, y: -100, radius: 250 };
        this.theme = 'light';
        this.hue = 220;
        this.time = 0;

        // Structured Flow Config
        this.config = {
            particleCount: 80,
            lineDistance: 180,
            baseSpeed: 0.4,
            pulseIntensity: 0,
            glowIntensity: 0,
            state: 'idle' // idle, processing, alert
        };

        this.init();
    }

    init() {
        this.canvas.id = 'bg-animation-canvas';
        this.canvas.style.position = 'fixed';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.width = '100vw';
        this.canvas.style.height = '100vh';
        this.canvas.style.zIndex = '-1';
        this.canvas.style.pointerEvents = 'none';
        this.canvas.style.opacity = '1';
        this.canvas.style.background = 'transparent';
        document.body.prepend(this.canvas);

        window.addEventListener('resize', () => this.resize());
        window.addEventListener('mousemove', (e) => {
            this.mouse.x = e.x;
            this.mouse.y = e.y;
        });

        this.resize();
        this.animate();

        // Observe theme changes
        const observer = new MutationObserver(() => this.updateTheme());
        observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
        this.updateTheme();
    }

    // --- Structured Flow Functions ---

    /**
     * Triggers a visual pulse event (e.g., on sale or update)
     */
    triggerPulse(intensity = 15) {
        this.config.pulseIntensity = intensity;
        // Temporary speed boost
        const originalSpeed = this.config.baseSpeed;
        this.config.baseSpeed *= 3;
        setTimeout(() => {
            this.config.baseSpeed = originalSpeed;
        }, 500);
    }

    /**
     * Sets the global flow state
     * @param {string} state - 'idle', 'processing', 'alert'
     */
    setFlowState(state) {
        this.config.state = state;
        switch (state) {
            case 'processing':
                this.config.baseSpeed = 0.8;
                this.config.glowIntensity = 0.5;
                break;
            case 'alert':
                this.config.baseSpeed = 1.2;
                this.config.glowIntensity = 1.0;
                break;
            default: // idle
                this.config.baseSpeed = 0.4;
                this.config.glowIntensity = 0;
        }
    }

    /**
     * Responds to real-time events from the platform
     */
    onEvent(eventType, data = {}) {
        console.log(`[NexusAnimation] Event: ${eventType}`, data);
        switch (eventType) {
            case 'sale':
                this.triggerPulse(20);
                break;
            case 'market_update':
                this.triggerPulse(10);
                if (data.volatility > 2) this.setFlowState('processing');
                else this.setFlowState('idle');
                break;
            case 'low_stock':
                this.setFlowState('alert');
                setTimeout(() => this.setFlowState('idle'), 5000);
                break;
            case 'ai_insight':
                this.triggerPulse(25);
                // Temporarily shift hue for AI moments
                const oldHue = this.hue;
                this.hue = 280; // Purple/Magic hue
                setTimeout(() => this.hue = oldHue, 2000);
                break;
        }
    }

    updateTheme() {
        const newTheme = document.documentElement.getAttribute('data-theme') || 'light';
        if (this.theme !== newTheme) {
            this.theme = newTheme;
            this.createParticles();
        }
    }

    resize() {
        this.width = this.canvas.width = window.innerWidth;
        this.height = this.canvas.height = window.innerHeight;
        this.createParticles();
    }

    getThemeColors() {
        switch (this.theme) {
            case 'dark':
                return {
                    primary: '60, 130, 246', // Blue 500
                    secondary: '147, 197, 253', // Blue 300
                    accent: '37, 99, 235', // Blue 600
                    bg: '10, 15, 30'
                };
            case 'eye-protection':
                return {
                    primary: '217, 119, 6', // Amber 600
                    secondary: '251, 191, 36', // Amber 400
                    accent: '146, 64, 14', // Amber 800
                    bg: '25, 20, 15'
                };
            default: // light
                return {
                    primary: '37, 99, 235', // Blue 600
                    secondary: '96, 165, 250', // Blue 400
                    accent: '29, 78, 216', // Blue 700
                    bg: '255, 255, 255'
                };
        }
    }

    createParticles() {
        this.particles = [];
        const count = Math.min(this.config.particleCount, Math.floor((this.width * this.height) / 15000));
        const colors = this.getThemeColors();

        for (let i = 0; i < count; i++) {
            this.particles.push({
                x: Math.random() * this.width,
                y: Math.random() * this.height,
                z: Math.random() * 3 + 1,
                vx: (Math.random() - 0.5) * this.config.baseSpeed,
                vy: (Math.random() - 0.5) * this.config.baseSpeed,
                size: Math.random() * 4 + 2,
                color: Math.random() > 0.5 ? colors.primary : colors.secondary,
                pulse: Math.random() * Math.PI * 2,
                pulseSpeed: 0.02 + Math.random() * 0.03
            });
        }
    }

    animate() {
        this.ctx.clearRect(0, 0, this.width, this.height);
        this.time += 0.01;
        const colors = this.getThemeColors();

        // Decay pulse and glow
        if (this.config.pulseIntensity > 0) this.config.pulseIntensity *= 0.95;

        this.particles.forEach((p, i) => {
            // Movement with depth-based speed and global baseSpeed
            p.x += p.vx * (1 / p.z) * (this.config.baseSpeed / 0.4);
            p.y += p.vy * (1 / p.z) * (this.config.baseSpeed / 0.4);

            // Screen wrap
            if (p.x < -50) p.x = this.width + 50;
            if (p.x > this.width + 50) p.x = -50;
            if (p.y < -50) p.y = this.height + 50;
            if (p.y > this.height + 50) p.y = -50;

            // Mouse repulsion/attraction logic
            const dx = this.mouse.x - p.x;
            const dy = this.mouse.y - p.y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            let extraSize = this.config.pulseIntensity * (1 / p.z);
            if (dist < this.mouse.radius) {
                const force = (1 - dist / this.mouse.radius);
                p.x -= dx * force * 0.03;
                p.y -= dy * force * 0.03;
                extraSize += force * 8;
            }

            // Pulse effect
            p.pulse += p.pulseSpeed;
            const pulseFactor = Math.sin(p.pulse) * 0.4 + 0.6;
            let opac = (0.4 + (1 / p.z) * 0.5) * pulseFactor;

            // Add state-based glow
            if (this.config.glowIntensity > 0) {
                opac = Math.min(1, opac + this.config.glowIntensity * 0.3);
            }

            // Draw particle (node)
            this.ctx.beginPath();
            this.ctx.arc(p.x, p.y, (p.size + extraSize) * (2 / p.z), 0, Math.PI * 2);

            // Highlight if in alert state
            let drawColor = p.color;
            if (this.config.state === 'alert' && Math.random() > 0.8) {
                drawColor = '239, 68, 68'; // Red 500
            }

            this.ctx.fillStyle = `rgba(${drawColor}, ${opac})`;
            this.ctx.fill();

            // Connections
            for (let j = i + 1; j < this.particles.length; j++) {
                const p2 = this.particles[j];
                const ldx = p.x - p2.x;
                const ldy = p.y - p2.y;
                const ldist = Math.sqrt(ldx * ldx + ldy * ldy);

                if (ldist < this.config.lineDistance) {
                    let lineOpac = (1 - ldist / this.config.lineDistance) * 0.3 * (1 / p.z);
                    if (this.config.pulseIntensity > 5) lineOpac *= 2;

                    this.ctx.beginPath();
                    this.ctx.moveTo(p.x, p.y);
                    this.ctx.lineTo(p2.x, p2.y);
                    this.ctx.strokeStyle = `rgba(${colors.primary}, ${lineOpac})`;
                    this.ctx.lineWidth = 0.8 + (this.config.pulseIntensity / 20);
                    this.ctx.stroke();
                }
            }
        });

        requestAnimationFrame(() => this.animate());
    }
}

// Initialized when the script loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.nexusAnimation = new NexusAnimation();
    });
} else {
    window.nexusAnimation = new NexusAnimation();
}
