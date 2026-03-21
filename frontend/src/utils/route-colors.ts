export const ROUTE_COLORS = [
  '#FB8500', // accent orange
  '#4785BF', // secondary blue
  '#2D9F4E', // forest green
  '#9B59B6', // amethyst
  '#E74C3C', // vermillion
  '#1ABC9C', // persian green
  '#E67E22', // carrot
  '#3498DB', // steel blue
]

export function getRouteColor(index: number): string {
  return ROUTE_COLORS[index % ROUTE_COLORS.length]
}
