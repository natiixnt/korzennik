import { Handle, Position, type NodeProps } from "reactflow";
import type { TreeNodeData } from "../../types/tree";

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "";
  // If it's YYYY-MM-DD from date picker, format nicely
  const iso = dateStr.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (iso) {
    const [, y, m, d] = iso;
    return `${parseInt(d)}.${parseInt(m)}.${y}`;
  }
  return dateStr;
}

export default function TreeNodeComponent({ data }: NodeProps<TreeNodeData>) {
  const name = [data.first_name, data.last_name].filter(Boolean).join(" ") || "???";
  const birth = formatDate(data.birthday);
  const death = formatDate(data.deathday);
  const dates = [birth, death].filter(Boolean).join(" - ");

  const isUserEntered = data.origin === "user_entered";
  const isAutoDiscovered = data.origin === "auto_discovered";

  const borderColor = isUserEntered
    ? "border-[var(--color-primary)]"
    : isAutoDiscovered
    ? "border-amber-400"
    : "border-blue-400";

  const bgColor = isUserEntered
    ? "bg-white"
    : isAutoDiscovered
    ? "bg-amber-50"
    : "bg-blue-50";

  const genderBar =
    data.gender === "M"
      ? "bg-blue-500"
      : data.gender === "F"
      ? "bg-pink-500"
      : "bg-gray-300";

  return (
    <div
      className={`rounded-xl border-2 shadow-md hover:shadow-lg transition-shadow min-w-[200px] max-w-[240px] overflow-hidden ${borderColor} ${bgColor}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-400 !w-2 !h-2 !border-2 !border-white" />

      <div className={`h-1 ${genderBar}`} />

      <div className="px-3 py-2.5">
        <div className="font-semibold text-sm text-gray-800 leading-tight">{name}</div>
        {dates && (
          <p className="text-xs text-gray-500 mt-0.5">{dates}</p>
        )}
        {data.birth_place && (
          <p className="text-[11px] text-gray-400 mt-0.5 truncate">{data.birth_place}</p>
        )}

        {!isUserEntered && (
          <div className="mt-1.5">
            <span
              className={`inline-block text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                isAutoDiscovered
                  ? "bg-amber-100 text-amber-700"
                  : "bg-blue-100 text-blue-700"
              }`}
            >
              {isAutoDiscovered ? "Odkryty" : "Ze zrodla"}
            </span>
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-gray-400 !w-2 !h-2 !border-2 !border-white" />
    </div>
  );
}
