/**
 * Status badge used in the QC variable progress strip.
 *
 * - When `known` is `false` or `value` is `undefined`, renders a **PENDING** amber badge
 *   (the variable has not yet been collected from the conversation).
 * - Otherwise renders the verdict string (`PASS` / `FAIL` / `WARN`) with matching colours.
 *
 * @param known - Whether the backend has marked this variable as fully collected.
 * @param value - The verdict string from `ChatState.variableStatuses`.
 */
function Chip({ known, value }: { known: boolean; value: string | undefined }) {
  if (!known || value === undefined) {
    return (
      <span className="px-xs text-label-xs sm:text-label-sm rounded border border-amber-300/40 bg-amber-100 py-0.5 font-bold text-amber-700">
        PENDING
      </span>
    );
  }

  const styles =
    value === 'FAIL'
      ? 'bg-red-100 text-red-700 border-red-300/40'
      : value === 'WARN'
        ? 'bg-amber-100 text-amber-700 border-amber-300/40'
        : 'bg-emerald-100 text-emerald-700 border-emerald-300/40';

  return (
    <span
      className={`px-xs text-label-xs sm:text-label-sm rounded border py-0.5 font-bold ${styles}`}
    >
      {value}
    </span>
  );
}

export default Chip;
