import { Colophon, Masthead } from '../components/landing/Chrome'
import { Story } from '../components/landing/Story.tsx'

export function Landing() {
  return (
    <div className="bg-canvas">
      <Masthead />
      <main>
        <Story />
      </main>
      <Colophon />
    </div>
  )
}
