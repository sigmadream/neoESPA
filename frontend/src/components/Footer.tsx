const Footer = () => {
  return (
    <footer className="border-t border-slate-100 dark:border-slate-900 bg-white dark:bg-slate-950 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-4">
        <p className="text-sm text-slate-400">
          &copy; {new Date().getFullYear()} neoESPA. All rights reserved.
        </p>
        <div className="flex gap-6 text-sm text-slate-400">
          <a href="#" className="hover:text-slate-600 dark:hover:text-slate-200 transition-colors">Privacy Policy</a>
          <a href="#" className="hover:text-slate-600 dark:hover:text-slate-200 transition-colors">Terms of Service</a>
          <a href="#" className="hover:text-slate-600 dark:hover:text-slate-200 transition-colors">Contact</a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
