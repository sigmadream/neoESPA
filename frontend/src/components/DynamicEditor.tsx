'use client';

import dynamic from 'next/dynamic';

const DynamicEditor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center text-sm text-slate-400">
      Loading Editor...
    </div>
  ),
});

export default DynamicEditor;
