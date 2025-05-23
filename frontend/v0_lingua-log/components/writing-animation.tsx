export function WritingAnimation({ text = "Writing" }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center space-y-2">
      <div className="text-base text-fun-purple font-medium">{text}</div>
      <div className="w-20 h-[3px] writing-line"></div>
    </div>
  )
}
