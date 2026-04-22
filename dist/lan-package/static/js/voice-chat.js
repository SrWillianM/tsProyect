/**
 * VoiceChat - WebRTC Voice Chat using simple-peer
 * 
 * Este módulo maneja:
 * - Conexión P2P de voz entre usuarios
 * - Señalización via Django Channels WebSocket
 * - Controles de mute/unmute
 * - Presencia de usuarios en voz
 */

class VoiceChat {
    constructor(options = {}) {
        this.roomName = options.roomName || '';
        this.alias = options.alias || 'Anonymous';
        this.wsUrl = options.wsUrl || '';

        const defaultIceServers = [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:global.stun.twilio.com:3478' }
        ];

        const configuredIceServers = Array.isArray(options.iceServers) && options.iceServers.length
            ? options.iceServers
            : defaultIceServers;
        
        // simple-peer configuration
        this.config = {
            iceServers: configuredIceServers
        };
        
        // Estado
        this.isConnected = false;
        this.isMuted = false;
        this.localStream = null;
        this.peers = new Map(); // peerId -> { peer, alias }
        this.voiceUsers = new Map(); // alias -> { connected, muted }
        
        // Elementos UI
        this.onVoiceStateChange = options.onVoiceStateChange || (() => {});
        this.onUserJoin = options.onUserJoin || (() => {});
        this.onUserLeave = options.onUserLeave || (() => {});
        this.onError = options.onError || console.error;
        
        // WebSocket de señalización
        this.socket = null;
        this.pendingCandidates = new Map(); // peerId -> candidates[]
    }

    /**
     * Inicializar conexión de voz
     */
    async connect() {
        try {
            const runningOnLocalhost = ['localhost', '127.0.0.1'].includes(window.location.hostname);
            if (!window.isSecureContext && !runningOnLocalhost) {
                this.onError('Para chat de voz fuera de localhost necesitas HTTPS. Publica el sitio con TLS antes de usar microfono.');
                return false;
            }

            // Obtener stream de audio
            this.localStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                },
                video: false
            });
            
            // El audio NO está muteado por defecto - el usuario puede hablar directamente
            // El mute es solo para silenciar, no para activar
            
            // Conectar WebSocket de señalización
            this._connectSignaling();
            
            return true;
        } catch (error) {
            this.onError('Error al conectar voz: ' + error.message);
            return false;
        }
    }

    /**
     * Conectar al WebSocket de señalización
     */
    _connectSignaling() {
        // Agregar parámetro de voz al URL
        const url = new URL(this.wsUrl);
        url.searchParams.set('voice', 'true');
        
        this.socket = new WebSocket(url.toString());
        
        this.socket.onopen = () => {
            console.log('[Voice] WebSocket de señalización conectado');
            this.isConnected = true;
            this._sendSignal({
                type: 'join',
                alias: this.alias
            });
            this.onVoiceStateChange({ connected: true });
        };
        
        this.socket.onmessage = (event) => {
            this._handleSignalingMessage(JSON.parse(event.data));
        };
        
        this.socket.onclose = () => {
            console.log('[Voice] WebSocket de señalización cerrado');
            this.isConnected = false;
            this._cleanupAllPeers();
            this.onVoiceStateChange({ connected: false });
        };
        
        this.socket.onerror = (error) => {
            this.onError('Error en WebSocket de señalización');
        };
    }

    /**
     * Manejar mensajes de señalización
     */
    _handleSignalingMessage(data) {
        console.log('[Voice] Mensaje recibido:', data);
        const { event, type, from, signal, users } = data;
        
        switch (event) {
            case 'voice_users':
                // Lista de usuarios en voz
                this._handleVoiceUsers(users);
                break;
                
            case 'user_joined_voice':
                // Nuevo usuario se unió a voz
                console.log('[Voice] Usuario se unió:', from);
                this._handleUserJoined(from);
                break;
                
            case 'user_left_voice':
                // Usuario salió de voz
                this._handleUserLeft(from);
                break;
                
            case 'signal':
                // Señal WebRTC (offer, answer, ice-candidate)
                console.log('[Voice] Señal recibida de:', from, 'tipo:', type);
                this._handleSignal(from, type, signal);
                break;
        }
    }

    /**
     * Manejar lista de usuarios en voz
     */
    _handleVoiceUsers(users) {
        console.log('[Voice] Recibida lista de usuarios en voz:', users);
        this.voiceUsers.clear();
        users.forEach(user => {
            this.voiceUsers.set(user.alias, {
                connected: true,
                muted: user.muted || false
            });
            console.log('[Voice] Creando conexión P2P hacia:', user.alias);
            // Crear conexión P2P hacia cada usuario existente (como iniciador)
            this._createPeerConnection(user.alias, true);
        });
        this.onUserJoin(Array.from(this.voiceUsers.keys()));
    }

    /**
     * Manejar usuario que se une
     */
    _handleUserJoined(alias) {
        if (alias === this.alias) return;
        
        if (!this.voiceUsers.has(alias)) {
            this.voiceUsers.set(alias, { connected: true, muted: false });
            console.log('[Voice] Usuario se unió, creando conexión como receptor:', alias);
            // El otro usuario ya creó como iniciador, crear como receptor
            this._createPeerConnection(alias, false);
            this.onUserJoin([alias]);
        }
    }

    /**
     * Manejar usuario que sale
     */
    _handleUserLeft(alias) {
        this.voiceUsers.delete(alias);
        this.onUserLeave([alias]);
        
        // Cerrar conexión P2P
        const peerObj = this.peers.get(alias);
        if (peerObj) {
            peerObj.peer.destroy();
            this.peers.delete(alias);
        }
    }

    /**
     * Crear conexión P2P (como iniciador o receptor)
     */
    _createPeerConnection(remoteAlias, initiator) {
        // Si ya existe, no crear de nuevo
        if (this.peers.has(remoteAlias)) {
            return;
        }
        
        // Verificar que tenemos stream local
        if (!this.localStream) {
            console.warn('[Voice] No hay stream local, no se puede crear peer');
            return;
        }
        
        const peer = new SimplePeer({
            initiator: initiator,
            stream: this.localStream,
            config: this.config,
            trickle: true
        });
        
        peer.on('signal', (signal) => {
            this._sendSignal({
                type: 'signal',
                to: remoteAlias,
                signal: signal
            });
        });
        
        peer.on('stream', (remoteStream) => {
            this._handleRemoteStream(remoteAlias, remoteStream);
        });
        
        peer.on('connect', () => {
            console.log(`[Voice] Conectado P2P con ${remoteAlias}`);
        });
        
        peer.on('close', () => {
            console.log(`[Voice] Conexión P2P cerrada con ${remoteAlias}`);
            this.peers.delete(remoteAlias);
        });
        
        peer.on('error', (err) => {
            console.error(`[Voice] Error con ${remoteAlias}:`, err);
            this.peers.delete(remoteAlias);
        });
        
        this.peers.set(remoteAlias, { peer, alias: remoteAlias });
        
        // Procesar candidatos pendientes
        const candidates = this.pendingCandidates.get(remoteAlias) || [];
        candidates.forEach(candidate => {
            peer.signal(candidate);
        });
        this.pendingCandidates.delete(remoteAlias);
    }

    /**
     * Manejar señal recibida (offer/answer/ice-candidate)
     */
    _handleSignal(from, type, signal) {
        // Ignorar señales que no son WebRTC reales
        if (type === 'join' || type === 'leave' || type === 'mute_status') {
            console.log('[Voice] Ignorando señal no-WebRTC:', type);
            return;
        }
        
        // Ignorar si signal es null o no existe
        if (!signal) {
            console.log('[Voice] Señal nula, ignorando');
            return;
        }
        
        let peerObj = this.peers.get(from);
        
        if (!peerObj) {
            // No existe conexión, crear como receptor
            this._createPeerConnection(from, false);
            peerObj = this.peers.get(from);
        }
        
        if (peerObj) {
            // Si es candidate, puede llegar antes de que esté listo
            if (signal.type === 'candidate') {
                try {
                    peerObj.peer.signal(signal);
                } catch (e) {
                    // Guardar para después
                    const candidates = this.pendingCandidates.get(from) || [];
                    candidates.push(signal);
                    this.pendingCandidates.set(from, candidates);
                }
            } else {
                peerObj.peer.signal(signal);
            }
        }
    }

    /**
     * Manejar stream remoto
     */
    _handleRemoteStream(alias, stream) {
        // Crear elemento de audio y reproducir
        const audio = new Audio();
        audio.srcObject = stream;
        audio.autoplay = true;
        audio.playsInline = true;
        
        // Guardar referencia
        const peerObj = this.peers.get(alias);
        if (peerObj) {
            peerObj.audio = audio;
        }
        
        console.log(`[Voice] Recibiendo audio de ${alias}`);
    }

    /**
     * Enviar señal via WebSocket
     */
    _sendSignal(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                event: 'voice_signal',
                ...data
            }));
        }
    }

    /**
     * Activar/desactivar micrófono
     */
    toggleMute() {
        if (!this.localStream) return false;
        
        this.isMuted = !this.isMuted;
        this.localStream.getAudioTracks().forEach(track => {
            track.enabled = !this.isMuted;
        });
        
        // Notificar a otros usuarios
        this._sendSignal({
            type: 'mute_status',
            muted: this.isMuted
        });
        
        this.onVoiceStateChange({ muted: this.isMuted });
        return this.isMuted;
    }

    /**
     * Obtener estado actual
     */
    getState() {
        return {
            connected: this.isConnected,
            muted: this.isMuted,
            usersInVoice: Array.from(this.voiceUsers.keys()),
            peerCount: this.peers.size
        };
    }

    /**
     * Desconectar
     */
    disconnect() {
        this._sendSignal({
            type: 'leave'
        });
        
        this._cleanupAllPeers();
        
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
        
        this.isConnected = false;
        this.voiceUsers.clear();
    }

    /**
     * Limpiar todas las conexiones P2P
     */
    _cleanupAllPeers() {
        this.peers.forEach((peerObj) => {
            if (peerObj.audio) {
                peerObj.audio.pause();
            }
            peerObj.peer.destroy();
        });
        this.peers.clear();
    }
}

// Exportar para uso global
window.VoiceChat = VoiceChat;