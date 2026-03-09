'use client'
import { useEffect, useRef, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'

// ─────────────────────────────────────────────────────
// AGENT STATES — the agent moves through these automatically
// ─────────────────────────────────────────────────────
type AgentState =
  | 'BOOTING'          // agent just started
  | 'REQUESTING_CAM'   // asking for camera permission
  | 'LOADING_MODELS'   // loading MediaPipe on-device
  | 'SCANNING_FACE'    // looking for a face
  | 'FACE_LOCKED'      // face found, waiting for gesture
  | 'GESTURE_DETECTED' // thumbs up seen, counting frames
  | 'AUTHENTICATED'    // auth complete
  | 'REDIRECTING'      // camera closed, navigating
  | 'ERROR'            // something went wrong

interface LogEntry {
  time: string
  state: AgentState | string
  message: string
  type: 'info' | 'success' | 'warn' | 'error'
}

export default function FaceAuthAgent() {
  const router       = useRouter()
  const videoRef     = useRef<HTMLVideoElement>(null)
  const canvasRef    = useRef<HTMLCanvasElement>(null)
  const streamRef    = useRef<MediaStream | null>(null)
  const cameraRef    = useRef<any>(null)           // holds MediaPipe Camera instance
  const thumbFrames  = useRef(0)
  const faceFrames   = useRef(0)
  const agentRunning = useRef(false)
  const REQUIRED_FRAMES = 18

  const [agentState, setAgentState] = useState<AgentState>('BOOTING')
  const [logs, setLogs]             = useState<LogEntry[]>([])
  const [faceConf, setFaceConf]     = useState(0)
  const [gestConf, setGestConf]     = useState(0)
  const [countdown, setCountdown]   = useState(0)
  const [errorMsg, setErrorMsg]     = useState('')

  // ── Add agent log ──────────────────────────────────
  const addLog = useCallback((
    message: string,
    type: LogEntry['type'] = 'info',
    state?: AgentState | string
  ) => {
    const time = new Date().toLocaleTimeString('en-GB', { hour12: false })
    setLogs(prev => [...prev.slice(-30), { time, state: state || '', message, type }])
  }, [])

  // ── Stop camera & release hardware ────────────────
  // Stops MediaPipe loop, kills hardware stream
  // (turns off MacBook camera LED), detaches video element
  const stopCamera = useCallback(async () => {
    // 1. Stop MediaPipe camera processing loop
    if (cameraRef.current) {
      try { await cameraRef.current.stop() } catch (_) {}
      cameraRef.current = null
    }
    // 2. Kill hardware stream tracks — turns off the camera LED
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        track.stop()
        track.enabled = false
      })
      streamRef.current = null
    }
    // 3. Detach stream from <video> element
    if (videoRef.current) {
      videoRef.current.srcObject = null
      videoRef.current.load()
    }
    // 4. Clear canvas overlay
    if (canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d')
      ctx?.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height)
    }
  }, [])

  // ── Draw face + hand overlays ──────────────────────
  const drawOverlay = useCallback((
    faceLandmarks: any[] | null,
    handLandmarks: any[] | null,
    thumbUp: boolean,
    state: AgentState
  ) => {
    const canvas = canvasRef.current
    const video  = videoRef.current
    if (!canvas || !video) return
    canvas.width  = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    const W = canvas.width, H = canvas.height

    if (faceLandmarks) {
      let minX = 1, maxX = 0, minY = 1, maxY = 0
      faceLandmarks.forEach((p: any) => {
        if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x
        if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y
      })
      const pad = 0.04
      const bx = (minX - pad) * W, by = (minY - pad) * H
      const bw = (maxX - minX + pad * 2) * W
      const bh = (maxY - minY + pad * 2) * H
      const col = (state === 'AUTHENTICATED' || state === 'REDIRECTING')
        ? '#00ff88' : thumbUp ? '#ffe033' : '#00e5ff'

      ctx.fillStyle   = `${col}15`; ctx.fillRect(bx, by, bw, bh)
      ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.strokeRect(bx, by, bw, bh)

      // Corner accents
      const cs = 16; ctx.lineWidth = 3
      const corners: [number,number,number,number,number,number][] = [
        [bx,    by,    cs,  0,  0,  cs],
        [bx+bw, by,   -cs,  0,  0,  cs],
        [bx,    by+bh,  cs,  0,  0, -cs],
        [bx+bw, by+bh, -cs,  0,  0, -cs],
      ]
      corners.forEach(([px,py,dx,dy,ex,ey]) => {
        ctx.beginPath(); ctx.moveTo(px+dx,py+dy); ctx.lineTo(px,py); ctx.lineTo(px+ex,py+ey); ctx.stroke()
      })

      // Status label above box
      const label = state === 'AUTHENTICATED' ? '✓ AUTHENTICATED'
        : state === 'GESTURE_DETECTED' ? `👍 HOLD... ${thumbFrames.current}/${REQUIRED_FRAMES}`
        : thumbUp ? '👍 GESTURE DETECTED' : 'FACE LOCKED'
      ctx.font = `bold ${Math.max(12, W * 0.02)}px monospace`
      const tw = ctx.measureText(label).width
      ctx.fillStyle = col; ctx.fillRect(bx, by - 26, tw + 14, 22)
      ctx.fillStyle = '#000'; ctx.fillText(label, bx + 7, by - 9)

      // Mesh dots
      ctx.fillStyle = `${col}60`
      ;[1, 33, 263, 61, 291, 199].forEach(i => {
        if (faceLandmarks[i]) {
          ctx.beginPath()
          ctx.arc(faceLandmarks[i].x * W, faceLandmarks[i].y * H, 2, 0, Math.PI * 2)
          ctx.fill()
        }
      })
    }

    if (handLandmarks) {
      const col = thumbUp ? '#ffe033' : '#9c6fff'
      const connections = [
        [0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],
        [5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],
        [13,17],[17,18],[18,19],[19,20],[0,17],
      ]
      ctx.strokeStyle = `${col}88`; ctx.lineWidth = 2
      connections.forEach(([a,b]) => {
        ctx.beginPath()
        ctx.moveTo(handLandmarks[a].x*W, handLandmarks[a].y*H)
        ctx.lineTo(handLandmarks[b].x*W, handLandmarks[b].y*H)
        ctx.stroke()
      })
      handLandmarks.forEach((p: any, i: number) => {
        ctx.beginPath(); ctx.arc(p.x*W, p.y*H, i===4?6:3, 0, Math.PI*2)
        ctx.fillStyle = i===4 ? col : `${col}bb`; ctx.fill()
      })
    }
  }, [])

  // ── Thumbs up geometry detection ──────────────────
  const isThumbsUp = (lm: any[]): boolean => {
    if (!lm || lm.length < 21) return false
    const thumbTip   = lm[4], thumbMcp  = lm[2]
    const fingerTips = [lm[8],  lm[12], lm[16], lm[20]]
    const fingerMcps = [lm[5],  lm[9],  lm[13], lm[17]]
    const thumbExtended = thumbTip.y < thumbMcp.y - 0.06
    const fingersCurled = fingerTips.filter((t, i) => t.y > fingerMcps[i].y - 0.02).length >= 3
    return thumbExtended && fingersCurled
  }

  // ── MAIN AGENT ─────────────────────────────────────
  const runAgent = useCallback(async () => {
    if (agentRunning.current) return
    agentRunning.current = true

    // ── STEP 1: Boot ────────────────────────────────
    setAgentState('BOOTING')
    addLog('FaceAuth Agent initialising...', 'info', 'BOOTING')
    addLog('On-device mode: MediaPipe FaceMesh + Hands', 'info', 'BOOTING')
    addLog('Zero data will be transmitted externally', 'success', 'BOOTING')
    await delay(800)

    // ── STEP 2: Request camera ───────────────────────
    setAgentState('REQUESTING_CAM')
    addLog('Requesting camera access...', 'info', 'REQUESTING_CAM')

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) videoRef.current.srcObject = stream
      addLog('Camera access granted ✓', 'success', 'REQUESTING_CAM')
    } catch (err: any) {
      setAgentState('ERROR')
      setErrorMsg('Camera permission denied. Allow camera access and refresh.')
      addLog(`Camera error: ${err.message}`, 'error', 'ERROR')
      agentRunning.current = false
      return
    }

    // ── STEP 3: Load MediaPipe models ────────────────
    setAgentState('LOADING_MODELS')
    addLog('Loading MediaPipe FaceMesh (468 landmarks)...', 'info', 'LOADING_MODELS')
    addLog('Loading MediaPipe Hands (21 landmarks)...', 'info', 'LOADING_MODELS')

    let FaceMeshClass: any, HandsClass: any, CameraClass: any
    try {
      const [fm, hd, cu] = await Promise.all([
        import('@mediapipe/face_mesh'),
        import('@mediapipe/hands'),
        import('@mediapipe/camera_utils'),
      ])
      FaceMeshClass = fm.FaceMesh
      HandsClass    = hd.Hands
      CameraClass   = cu.Camera
      addLog('All models loaded ✓ (running on-device)', 'success', 'LOADING_MODELS')
    } catch (err: any) {
      setAgentState('ERROR')
      setErrorMsg('Failed to load AI models. Check internet connection.')
      addLog(`Model load error: ${err.message}`, 'error', 'ERROR')
      agentRunning.current = false
      return
    }

    // ── STEP 4: Init detectors ───────────────────────
    const video = videoRef.current!
    let latestFace: any  = null
    let latestHands: any = null

    const faceMesh = new FaceMeshClass({
      locateFile: (f: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${f}`,
    })
    faceMesh.setOptions({
      maxNumFaces: 1,
      refineLandmarks: true,
      minDetectionConfidence: 0.6,
      minTrackingConfidence: 0.6,
    })
    faceMesh.onResults((r: any) => { latestFace = r })

    const hands = new HandsClass({
      locateFile: (f: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${f}`,
    })
    hands.setOptions({
      maxNumHands: 1,
      modelComplexity: 1,
      minDetectionConfidence: 0.7,
      minTrackingConfidence: 0.6,
    })
    hands.onResults((r: any) => { latestHands = r })

    // ── STEP 5: Start scanning loop ──────────────────
    setAgentState('SCANNING_FACE')
    addLog('Agent scanning for face...', 'info', 'SCANNING_FACE')

    let currentState: AgentState = 'SCANNING_FACE'
    let authDone = false

    const camera = new CameraClass(video, {
      onFrame: async () => {
        if (authDone) return

        await faceMesh.send({ image: video })
        await hands.send({ image: video })

        const hasFace = latestFace?.multiFaceLandmarks?.length > 0
        const hasHand = latestHands?.multiHandLandmarks?.length > 0
        const faceLm  = hasFace ? latestFace.multiFaceLandmarks[0]  : null
        const handLm  = hasHand ? latestHands.multiHandLandmarks[0] : null
        const thumbUp = hasHand ? isThumbsUp(handLm) : false

        // Track face stability across frames
        if (hasFace) faceFrames.current = Math.min(faceFrames.current + 1, 30)
        else         faceFrames.current = Math.max(faceFrames.current - 2, 0)
        const faceStable = faceFrames.current >= 5

        // Track thumbs up across frames
        if (thumbUp && faceStable) thumbFrames.current++
        else                       thumbFrames.current = Math.max(thumbFrames.current - 1, 0)

        // Update confidence UI
        const fc = Math.min(99, Math.round((faceFrames.current / 5) * 95))
        const gc = Math.min(99, Math.round((thumbFrames.current / REQUIRED_FRAMES) * 99))
        setFaceConf(fc)
        setGestConf(gc)
        setCountdown(Math.max(0, REQUIRED_FRAMES - thumbFrames.current))

        // ── State machine transitions ──────────────
        if (!hasFace && currentState !== 'SCANNING_FACE') {
          currentState = 'SCANNING_FACE'
          setAgentState('SCANNING_FACE')
          addLog('Face lost — rescanning...', 'warn', 'SCANNING_FACE')
          thumbFrames.current = 0

        } else if (hasFace && !thumbUp && currentState === 'SCANNING_FACE') {
          currentState = 'FACE_LOCKED'
          setAgentState('FACE_LOCKED')
          addLog('Face detected and locked ✓', 'success', 'FACE_LOCKED')
          addLog('Waiting for thumbs up gesture...', 'info', 'FACE_LOCKED')

        } else if (thumbUp && faceStable && currentState === 'FACE_LOCKED') {
          currentState = 'GESTURE_DETECTED'
          setAgentState('GESTURE_DETECTED')
          addLog('👍 Thumbs up detected! Hold steady...', 'success', 'GESTURE_DETECTED')

        } else if (currentState === 'GESTURE_DETECTED' && !thumbUp) {
          currentState = 'FACE_LOCKED'
          setAgentState('FACE_LOCKED')
          addLog('Gesture lost — show thumbs up again', 'warn', 'FACE_LOCKED')

        } else if (thumbFrames.current >= REQUIRED_FRAMES && faceStable) {
          // ── AUTH SUCCESS ──────────────────────────
          authDone = true
          currentState = 'AUTHENTICATED'
          setAgentState('AUTHENTICATED')
          addLog('Authentication successful ✓', 'success', 'AUTHENTICATED')
          addLog('Setting session cookie...', 'info', 'AUTHENTICATED')
          document.cookie = 'face_auth=granted; path=/; max-age=3600'

          // Short pause so user sees the green success state
          await delay(900)

          // ── STOP CAMERA BEFORE NAVIGATING ────────
          // This turns off the MacBook camera LED
          setAgentState('REDIRECTING')
          addLog('Stopping camera & releasing hardware...', 'info', 'REDIRECTING')

          // 1. Stop MediaPipe processing loop
          try { await camera.stop() } catch (_) {}

          // 2. Stop all hardware tracks → turns off camera LED
          streamRef.current?.getTracks().forEach(track => {
            track.stop()
            track.enabled = false
          })
          streamRef.current = null

          // 3. Detach stream from <video> element
          if (videoRef.current) {
            videoRef.current.srcObject = null
            videoRef.current.load()
          }

          // 4. Clear overlay canvas
          if (canvasRef.current) {
            const ctx = canvasRef.current.getContext('2d')
            ctx?.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height)
          }

          addLog('Camera closed ✓ — LED off', 'success', 'REDIRECTING')
          addLog('Redirecting to dashboard...', 'info', 'REDIRECTING')

          await delay(400)
          router.push('/')
          return
        }

        drawOverlay(faceLm, handLm, thumbUp, currentState)
      },
      width: 640,
      height: 480,
    })

    // Store in ref so cleanup can also access it
    cameraRef.current = camera
    await camera.start()
    addLog('Camera stream active — agent running autonomously', 'success', 'SCANNING_FACE')

  }, [addLog, drawOverlay, stopCamera, router])

  // ── Auto-start agent on mount ──────────────────────
  useEffect(() => {
    const timer = setTimeout(runAgent, 500)

    // Cleanup on component unmount (back navigation, hot reload, etc.)
    return () => {
      clearTimeout(timer)
      // Stop MediaPipe loop
      if (cameraRef.current) {
        try { cameraRef.current.stop() } catch (_) {}
        cameraRef.current = null
      }
      // Kill hardware camera tracks
      streamRef.current?.getTracks().forEach(track => {
        track.stop()
        track.enabled = false
      })
      streamRef.current = null
      // Detach from video element
      if (videoRef.current) {
        videoRef.current.srcObject = null
      }
    }
  }, [runAgent])

  // ── Retry after error ──────────────────────────────
  const retry = () => {
    agentRunning.current = false
    thumbFrames.current  = 0
    faceFrames.current   = 0
    setLogs([])
    setFaceConf(0)
    setGestConf(0)
    setErrorMsg('')
    runAgent()
  }

  // ── RENDER ─────────────────────────────────────────
  return (
    <div style={s.page}>
      <div style={s.wrap}>

        {/* Privacy badge */}
        <div style={s.privacyBadge}>
          🛡️ <strong style={{ color: '#fff' }}>100% On-Device</strong> — Zero data transmitted externally
        </div>

        {/* Logo + state badge */}
        <div style={s.header}>
          <div style={s.logo}>Face<span style={{ color: '#c8e8f0' }}>Agent</span></div>
          <AgentStateBadge state={agentState} />
        </div>

        {/* Camera feed */}
        <div style={s.camBox}>
          <div style={s.camHeader}>
            <span style={s.camLabel}>📷 AUTONOMOUS SCANNER</span>
            <span style={{ fontSize: 10, color: '#2a5060', letterSpacing: 1 }}>
              {agentState === 'REDIRECTING' ? '→ REDIRECTING' : 'AGENT CONTROLLED'}
            </span>
          </div>
          <div style={s.camFeed}>

            {/* Loading overlay */}
            {(agentState === 'BOOTING' ||
              agentState === 'REQUESTING_CAM' ||
              agentState === 'LOADING_MODELS') && (
              <div style={s.overlay}>
                <div style={s.spinner} />
                <div style={s.overlayText}>{AGENT_STATE_LABELS[agentState]}</div>
              </div>
            )}

            {/* Error overlay */}
            {agentState === 'ERROR' && (
              <div style={s.overlay}>
                <div style={{ fontSize: 36, marginBottom: 12 }}>⚠️</div>
                <div style={{ color: '#ff2d6e', fontSize: 13, marginBottom: 16, textAlign: 'center' }}>
                  {errorMsg}
                </div>
                <button style={s.retryBtn} onClick={retry}>↺ RETRY</button>
              </div>
            )}

            {/* Auth success + redirecting overlay — camera already stopped */}
            {(agentState === 'AUTHENTICATED' || agentState === 'REDIRECTING') && (
              <div style={{ ...s.overlay, background: 'rgba(0,255,136,0.1)' }}>
                <div style={{ fontSize: 52, marginBottom: 12 }}>✅</div>
                <div style={{ color: '#00ff88', fontSize: 14, letterSpacing: 2, marginBottom: 8 }}>
                  AUTHENTICATED
                </div>
                {agentState === 'REDIRECTING' && (
                  <div style={{ color: '#2a5060', fontSize: 11, letterSpacing: 1 }}>
                    📷 Camera closed · Redirecting...
                  </div>
                )}
              </div>
            )}

            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{
                width: '100%',
                display: 'block',
                transform: 'scaleX(-1)',
                // Hide video during non-scanning states
                opacity: ['BOOTING','REQUESTING_CAM','LOADING_MODELS',
                          'ERROR','AUTHENTICATED','REDIRECTING'].includes(agentState) ? 0 : 1,
              }}
            />
            <canvas
              ref={canvasRef}
              style={{
                position: 'absolute', top: 0, left: 0,
                width: '100%', height: '100%',
                pointerEvents: 'none',
              }}
            />
          </div>
        </div>

        {/* Confidence bars */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
          <ConfBar label="FACE"    value={faceConf} color="#00e5ff" />
          <ConfBar label="GESTURE" value={gestConf} color="#ffe033" />
          {agentState === 'GESTURE_DETECTED' && (
            <ConfBar
              label="HOLD STEADY"
              value={Math.round(((REQUIRED_FRAMES - countdown) / REQUIRED_FRAMES) * 100)}
              color="#00ff88"
            />
          )}
        </div>

        {/* Step progress */}
        <AgentSteps state={agentState} />

        {/* Execution log */}
        <AgentLog logs={logs} />

      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────
// SUB-COMPONENTS
// ─────────────────────────────────────────────────────

const AGENT_STATE_LABELS: Partial<Record<AgentState, string>> = {
  BOOTING:          'Agent booting...',
  REQUESTING_CAM:   'Requesting camera...',
  LOADING_MODELS:   'Loading AI models...',
  SCANNING_FACE:    'Scanning for face...',
  FACE_LOCKED:      'Face locked — show 👍',
  GESTURE_DETECTED: 'Gesture detected — hold...',
  AUTHENTICATED:    'Authenticated!',
  REDIRECTING:      'Camera closed · Redirecting...',
  ERROR:            'Error',
}

const STATE_COLORS: Partial<Record<AgentState, string>> = {
  BOOTING:          '#2a5060',
  REQUESTING_CAM:   '#ffe033',
  LOADING_MODELS:   '#ffe033',
  SCANNING_FACE:    '#00e5ff',
  FACE_LOCKED:      '#00e5ff',
  GESTURE_DETECTED: '#ffe033',
  AUTHENTICATED:    '#00ff88',
  REDIRECTING:      '#00ff88',
  ERROR:            '#ff2d6e',
}

function AgentStateBadge({ state }: { state: AgentState }) {
  const col = STATE_COLORS[state] || '#2a5060'
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6,
      fontSize: 11, padding: '5px 12px', borderRadius: 10,
      border: `1px solid ${col}`, color: col,
      letterSpacing: 1, fontFamily: 'monospace',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: col, boxShadow: `0 0 6px ${col}` }} />
      {AGENT_STATE_LABELS[state] || state}
    </div>
  )
}

const STEPS: { key: AgentState; label: string; icon: string }[] = [
  { key: 'BOOTING',          label: 'Boot',    icon: '⚡' },
  { key: 'LOADING_MODELS',   label: 'Models',  icon: '🧠' },
  { key: 'SCANNING_FACE',    label: 'Face',    icon: '👤' },
  { key: 'FACE_LOCKED',      label: 'Lock',    icon: '🎯' },
  { key: 'GESTURE_DETECTED', label: 'Gesture', icon: '👍' },
  { key: 'AUTHENTICATED',    label: 'Auth',    icon: '✅' },
]

const STEP_ORDER: AgentState[] = [
  'BOOTING','REQUESTING_CAM','LOADING_MODELS',
  'SCANNING_FACE','FACE_LOCKED','GESTURE_DETECTED',
  'AUTHENTICATED','REDIRECTING',
]

function AgentSteps({ state }: { state: AgentState }) {
  const currentIdx = STEP_ORDER.indexOf(state)
  return (
    <div style={{
      display: 'flex', alignItems: 'center', marginBottom: 12,
      background: '#091520', border: '1px solid #0d2030',
      borderRadius: 10, padding: '12px 16px', gap: 0,
    }}>
      {STEPS.map((step, i) => {
        const stepIdx = STEP_ORDER.indexOf(step.key)
        const done    = currentIdx > stepIdx
        const active  = currentIdx === stepIdx ||
          (step.key === 'LOADING_MODELS' && state === 'REQUESTING_CAM')
        return (
          <div key={step.key} style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
              <div style={{
                width: 32, height: 32, borderRadius: '50%',
                background: done ? '#00ff88' : active ? '#00e5ff' : '#0d2030',
                border: `2px solid ${done ? '#00ff88' : active ? '#00e5ff' : '#1a3040'}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 14, transition: 'all 0.3s',
                boxShadow: active ? '0 0 10px #00e5ff' : done ? '0 0 8px #00ff88' : 'none',
              }}>
                {step.icon}
              </div>
              <div style={{
                fontSize: 8,
                color: done ? '#00ff88' : active ? '#00e5ff' : '#2a5060',
                letterSpacing: 0.5, fontFamily: 'monospace',
              }}>
                {step.label}
              </div>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{
                flex: 1, height: 2,
                background: done ? '#00ff88' : '#0d2030',
                margin: '0 2px', marginBottom: 16,
                transition: 'background 0.3s',
              }} />
            )}
          </div>
        )
      })}
    </div>
  )
}

function AgentLog({ logs }: { logs: LogEntry[] }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [logs])

  const typeColors: Record<string, string> = {
    info: '#2a5060', success: '#00ff88', warn: '#ffe033', error: '#ff2d6e',
  }

  return (
    <div style={{ background: '#060d14', border: '1px solid #0d2030', borderRadius: 10, overflow: 'hidden' }}>
      <div style={{
        padding: '8px 14px', borderBottom: '1px solid #0d2030',
        fontSize: 9, letterSpacing: 2, color: '#00e5ff',
      }}>
        ● AGENT EXECUTION LOG
      </div>
      <div ref={ref} style={{
        height: 140, overflowY: 'auto', padding: '8px 14px',
        fontFamily: 'monospace', fontSize: 11, lineHeight: 1.9,
      }}>
        {logs.length === 0 && <div style={{ color: '#2a5060' }}>Waiting for agent...</div>}
        {logs.map((log, i) => (
          <div key={i} style={{ color: typeColors[log.type] || '#2a5060' }}>
            [{log.time}] {log.message}
          </div>
        ))}
      </div>
    </div>
  )
}

function ConfBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{
      flex: 1, background: '#091520',
      border: '1px solid #0d2030', borderRadius: 8, padding: '10px 12px',
    }}>
      <div style={{ fontSize: 9, color: '#2a5060', letterSpacing: 1, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 800, color, fontFamily: 'monospace', marginBottom: 5 }}>
        {value}%
      </div>
      <div style={{ height: 3, background: '#0d2030', borderRadius: 2 }}>
        <div style={{
          height: '100%', width: `${value}%`, background: color,
          borderRadius: 2, transition: 'width 0.3s',
        }} />
      </div>
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────
function delay(ms: number) {
  return new Promise(r => setTimeout(r, ms))
}

// ── Styles ────────────────────────────────────────────
const s: Record<string, React.CSSProperties> = {
  page: {
    background: '#03060a', minHeight: '100vh',
    display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
  },
  wrap: {
    width: '100%', maxWidth: 500,
    fontFamily: "'Share Tech Mono', monospace", color: '#c8e8f0',
  },
  privacyBadge: {
    background: 'rgba(0,255,136,0.07)', border: '1px solid rgba(0,255,136,0.25)',
    borderRadius: 10, padding: '9px 14px', marginBottom: 16,
    fontSize: 11, color: '#00ff88', letterSpacing: 0.5, lineHeight: 1.7,
  },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16,
  },
  logo: {
    fontFamily: 'monospace', fontSize: 24, fontWeight: 900, color: '#00e5ff', letterSpacing: 3,
  },
  camBox: {
    background: '#060d14', border: '1px solid #0d2030',
    borderRadius: 14, overflow: 'hidden', marginBottom: 12,
  },
  camHeader: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '10px 16px', borderBottom: '1px solid #0d2030',
  },
  camLabel: { fontSize: 10, letterSpacing: 2, color: '#00e5ff' },
  camFeed: {
    position: 'relative', background: '#000',
    aspectRatio: '4/3' as any, overflow: 'hidden',
  },
  overlay: {
    position: 'absolute', inset: 0,
    background: 'rgba(3,6,10,0.88)',
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    zIndex: 10, gap: 12,
  },
  overlayText: { color: '#00e5ff', fontSize: 13, letterSpacing: 2, fontFamily: 'monospace' },
  spinner: {
    width: 36, height: 36,
    border: '3px solid rgba(0,229,255,0.2)',
    borderTopColor: '#00e5ff', borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  retryBtn: {
    background: '#00e5ff', color: '#000', border: 'none', borderRadius: 6,
    padding: '10px 22px', fontFamily: 'monospace', fontSize: 12,
    fontWeight: 700, cursor: 'pointer', letterSpacing: 1,
  },
}
