// Swedish singular/plural picker. `plural(1, 'träff', 'träffar')` → 'träff',
// any other count → 'träffar'. Keeps inline ternaries out of JSX.
export function plural(n: number, singular: string, pluralForm: string): string {
  return n === 1 ? singular : pluralForm;
}
