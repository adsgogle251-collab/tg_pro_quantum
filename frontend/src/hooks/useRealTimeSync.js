/**
 * useRealTimeSync – Sprint 3
 *
 * Connects to the FastAPI native WebSocket endpoint
 * ``/api/v1/ws/client/{clientId}`` and dispatches account-related events
 * so the Accounts page can update without a manual refresh.
 *
 * Usage:
 *   const { connected, lastEvent } = useRealTimeSync(clientId, onEvent)
 *
 * ``onEvent(payload)`` is called for every incoming message. The hook
 * also returns the most recent event payload so you can react in useEffect.
 *
 * Event types emitted by the backend:
 *   account.imported       – session import finished
 *   account.bulk_created   – bulk create finished
 *   account.file_imported  – file import finished
 *   account.otp_setup      – OTP secret generated
 *   account.otp_verified   – OTP verified / 2FA activated
 *   account.updated        – account record changed
 *   account.deleted        – account deleted
 */
import { useEffect, useRef, useState, useCallback } from 'react'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'
// Convert http(s)://host to ws(s)://host
const WS_BASE = API_BASE.replace(/^http/, 'ws').replace(/\/api\/v1$/, '')

const RECONNECT_DELAY_MS = 3000
const MAX_RECONNECT_ATTEMPTS = 10

export function useRealTimeSync(clientId, onEvent) {
  const [connected, setConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState(null)
  const wsRef = useRef(null)
  const attemptsRef = useRef(0)
  const timerRef = useRef(null)
  const onEventRef = useRef(onEvent)

  // Keep onEvent ref up-to-date without re-running the effect
  useEffect(() => { onEventRef.current = onEvent }, [onEvent])

  const connect = useCallback(() => {
    if (!clientId) return
    const token = localStorage.getItem('access_token')
    const url = `${WS_BASE}/ws/client/${clientId}${token ? `?token=${token}` : ''}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      attemptsRef.current = 0
    }

    ws.onmessage = (evt) => {
      let payload
      try { payload = JSON.parse(evt.data) } catch { return }

      // Only handle account-related events
      if (typeof payload.event === 'string' && payload.event.startsWith('account.')) {
        setLastEvent(payload)
        onEventRef.current?.(payload)
      }
    }

    ws.onclose = () => {
      setConnected(false)
      if (attemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        attemptsRef.current += 1
        timerRef.current = setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [clientId])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { connected, lastEvent }
}

export default useRealTimeSync
