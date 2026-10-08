import React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";

// Court page modal shell (soft purple blurred overlay, white rounded card, close X).
export function CourtDialog({ open, onClose, testid, title, desc, children, wide = false, bare = false }) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-[60] bg-[rgba(32,18,54,0.55)] backdrop-blur-[4px] data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <DialogPrimitive.Content
          data-testid={testid}
          className={`fixed left-1/2 top-1/2 z-[61] -translate-x-1/2 -translate-y-1/2 w-[calc(100%-1.5rem)] ${wide ? "max-w-[650px]" : "max-w-[540px]"} bg-white rounded-[20px] shadow-[0_15px_35px_rgba(0,0,0,0.25)] focus:outline-none data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95 ${
            bare ? "overflow-hidden" : "p-6 sm:p-7 max-h-[88vh] overflow-y-auto"
          }`}
        >
          {bare ? (
            <>
              <DialogPrimitive.Title className="sr-only">{title}</DialogPrimitive.Title>
              <DialogPrimitive.Description className="sr-only">{desc}</DialogPrimitive.Description>
            </>
          ) : (
            <>
              <DialogPrimitive.Title className="text-[1.3rem] font-bold text-[#3b1566] pr-8 leading-snug mb-2">{title}</DialogPrimitive.Title>
              <DialogPrimitive.Description className="text-[0.92rem] text-[#5f6368] leading-relaxed mb-5">{desc}</DialogPrimitive.Description>
            </>
          )}
          {children}
          {!bare && (
            <DialogPrimitive.Close
              data-testid={`${testid}-close`}
              aria-label="Close"
              className="absolute top-[18px] right-[18px] w-8 h-8 rounded-full text-[#888] hover:text-[#3b1566] hover:bg-[#f2ebfc] flex items-center justify-center transition-colors"
            >
              <i className="fa-solid fa-xmark text-lg"></i>
            </DialogPrimitive.Close>
          )}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
