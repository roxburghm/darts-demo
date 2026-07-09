import { ref, onUnmounted } from 'vue'
import type { WebSocketMessage } from '@/api/types'

export function useWebSocket(sessionId: string) {
  const connected = ref(false)
  const lastMessage = ref<WebSocketMessage | null>(null)
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectDelay = 1000

  const handlers: Map<string, ((msg: WebSocketMessage) => void)[]> = new Map()

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/api/ws/${sessionId}`

    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
      reconnectDelay = 1000
    }

    ws.onmessage = (event) => {
      try {
        const msg: WebSocketMessage = JSON.parse(event.data)
        if (msg.type === 'ping') return

        lastMessage.value = msg
        const typeHandlers = handlers.get(msg.type)
        if (typeHandlers) {
          typeHandlers.forEach((h) => h(msg))
        }
        // Also fire wildcard handlers
        const allHandlers = handlers.get('*')
        if (allHandlers) {
          allHandlers.forEach((h) => h(msg))
        }
      } catch {
        // Ignore malformed messages
      }
    }

    ws.onclose = () => {
      connected.value = false
      scheduleReconnect()
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer) return
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      reconnectDelay = Math.min(reconnectDelay * 2, 16000)
      connect()
    }, reconnectDelay)
  }

  function on(type: string, handler: (msg: WebSocketMessage) => void) {
    if (!handlers.has(type)) {
      handlers.set(type, [])
    }
    handlers.get(type)!.push(handler)
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.onclose = null
      ws.close()
      ws = null
    }
    connected.value = false
  }

  connect()

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    lastMessage,
    on,
    disconnect,
  }
}
