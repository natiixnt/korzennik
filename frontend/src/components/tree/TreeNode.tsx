import { Handle, Position, type NodeProps } from "reactflow";
import type { TreeNodeData } from "../../types/tree";

export default function TreeNodeComponent({ data }: NodeProps<TreeNodeData>) {
  const name = [data.first_name, data.last_name].filter(Boolean).join(" ") || "???";
  const dates = [data.birthday, data.deathday].filter(Boolean).join(" - ");

  const borderColor =
    data.origin === "user_entered"
      ? "border-[var(--color-primary)]"
      : "border-blue-400";

  const genderIcon =
    data.gender === "M" ? "bg-blue-400" : data.gender === "F" ? "bg-pink-400" : "bg-gray-300";

  return (
    <div
      className={`px-4 py-3 rounded-lg border-2 bg-white shadow-md min-w-[200px] ${borderColor}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-400" />
      <div className="flex items-center gap-2">
        <span className={`inline-block w-2.5 h-2.5 rounded-full ${genderIcon}`} />
        <span className="font-semibold text-sm">{name}</span>
      </div>
      {dates && <p className="text-xs text-gray-500 mt-1">{dates}</p>}
      {data.birth_place && (
        <p className="text-xs text-gray-400">{data.birth_place}</p>
      )}
      <Handle type="source" position={Position.Bottom} className="!bg-gray-400" />
    </div>
  );
}
