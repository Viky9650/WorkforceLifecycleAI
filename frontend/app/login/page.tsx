'use client'
import dynamic from 'next/dynamic'

const FaceAuthAgent = dynamic(
  () => import('@/components/FaceAuthAgent'),
  {
    ssr: false,
    loading: () => (
      <div style={{
        background: '#03060a', minHeight: '100vh',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#00e5ff', fontFamily: 'monospace', fontSize: 13, letterSpacing: 2
      }}>
        ⚡ INITIALISING AGENT...
      </div>
    )
  }
)

export default function LoginPage() {
  return <FaceAuthAgent />
}