import { Heading } from '../components/heading'
import { Text } from '../components/text'

export function DashboardPage() {
  return (
    <div>
      <Heading className="font-heading">Today's Work</Heading>
      <Text className="mt-2">No jobs loaded. Connect your system of record to see today's schedule.</Text>
    </div>
  )
}
