import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'

export function CountUp({ value, duration = 800, className = '' }) {
  const [display, setDisplay] = useState(0)
  const num = typeof value === 'number' ? value : parseFloat(value) || 0

  useEffect(() => {
    if (num === 0) {
      setDisplay(0)
      return
    }
    const start = performance.now()
    const tick = (now) => {
      const p = Math.min((now - start) / duration, 1)
      const eased = 1 - (1 - p) ** 3
      setDisplay(Math.round(num * eased))
      if (p < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [num, duration])

  return <span className={className}>{display.toLocaleString()}</span>
}
