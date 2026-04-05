import { useState, useEffect } from 'react'
import wsService from '../services/websocket'

export function useRealtime(event) {
  const [data, setData] = useState(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    wsService.connect()

    const onData = (payload) => setData(payload)
    const onConnect = () => setConnected(true)
    const onDisconnect = () => setConnected(false)

    wsService.subscribe(event, onData)
    wsService.subscribe('connect', onConnect)
    wsService.subscribe('disconnect', onDisconnect)

    setConnected(wsService.connected)

    return () => {
      wsService.unsubscribe(event, onData)
      wsService.unsubscribe('connect', onConnect)
      wsService.unsubscribe('disconnect', onDisconnect)
    }
  }, [event])

  return { data, connected }
}

export default useRealtime
