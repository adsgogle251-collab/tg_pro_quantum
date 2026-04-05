import { io } from 'socket.io-client'

let socket = null
const listeners = {}

const wsService = {
  connect() {
    if (socket?.connected) return
    socket = io(import.meta.env.VITE_WS_URL ?? 'http://localhost:8000', {
      path: '/ws/',
      transports: ['websocket'],
      autoConnect: true,
    })
    socket.on('connect', () => console.log('[WS] connected'))
    socket.on('disconnect', () => console.log('[WS] disconnected'))
  },

  disconnect() {
    socket?.disconnect()
    socket = null
  },

  subscribe(event, cb) {
    if (!socket) this.connect()
    if (!listeners[event]) listeners[event] = []
    listeners[event].push(cb)
    socket.on(event, cb)
  },

  unsubscribe(event, cb) {
    if (!socket) return
    if (cb) {
      socket.off(event, cb)
      listeners[event] = (listeners[event] || []).filter((l) => l !== cb)
    } else {
      socket.off(event)
      delete listeners[event]
    }
  },

  get connected() {
    return socket?.connected ?? false
  },
}

export default wsService
