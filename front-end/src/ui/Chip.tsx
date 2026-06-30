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
      <span className="rounded border border-[#b45d00]/20 bg-[#fff4e5] px-xs py-[2px] text-[10px] font-bold text-[#b45d00]">
        PENDING
      </span>
    );
  }

  const styles =
    value === 'FAIL'
      ? 'bg-red-100 text-red-700 border-red-300/40'
      : value === 'WARN'
        ? 'bg-[#fff4e5] text-[#b45d00] border-[#b45d00]/20'
        : 'bg-[#e6f4ea] text-[#1e7e34] border-[#1e7e34]/20';

  return (
    <span className={`rounded border px-xs py-[2px] text-[10px] font-bold ${styles}`}>
      {value}
    </span>
  );
}

export default Chip;
