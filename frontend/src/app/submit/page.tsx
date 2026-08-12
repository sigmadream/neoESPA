import { redirect } from 'next/navigation';

export default async function SubmitPage({
  searchParams,
}: {
  searchParams: Promise<{ hwNum?: string }>;
}) {
  const params = await searchParams;
  if (params.hwNum) {
    redirect(`/homework/${params.hwNum}#submission-panel`);
  }
  redirect('/homework');
}
