import { redirect } from 'next/navigation';

export default async function SubmitResultPage({
  searchParams,
}: {
  searchParams: Promise<{ id?: string }>;
}) {
  const params = await searchParams;
  if (params.id) {
    redirect(`/homework/result?id=${params.id}`);
  }
  redirect('/homework/result');
}
