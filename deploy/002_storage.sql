insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
 values ('career-resumes-private','career-resumes-private',false,10485760,array['application/pdf'])
 on conflict(id) do nothing;
do $$ begin
 if (select public from storage.buckets where id='career-resumes-private') then raise exception 'Resume bucket must be private'; end if;
end $$;
-- Downloads/uploads use the authenticated application backend, including owner and app RLS checks.
-- No direct client access even if another bucket has permissive policies.
drop policy if exists career_backend_only on storage.objects;
create policy career_backend_only on storage.objects as restrictive for all to anon,authenticated
 using (bucket_id <> 'career-resumes-private') with check (bucket_id <> 'career-resumes-private');
