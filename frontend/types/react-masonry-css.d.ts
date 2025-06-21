declare module 'react-masonry-css' {
  import { ReactNode } from 'react';

  interface MasonryProps {
    breakpointCols?: number | { [key: number]: number; default: number };
    className?: string;
    columnClassName?: string;
    children?: ReactNode;
  }

  const Masonry: React.FC<MasonryProps>;
  export default Masonry;
}
