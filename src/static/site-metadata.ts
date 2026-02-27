interface ISiteMetadataResult {
  siteTitle: string;
  siteUrl: string;
  description: string;
  logo: string;
  navLinks: {
    name: string;
    url: string;
  }[];
}

// const getBasePath = () => {
//   const baseUrl = import.meta.env.BASE_URL;
//   return baseUrl === '/' ? '' : baseUrl;
// };

const data: ISiteMetadataResult = {
  siteTitle: "Cigar's Running Page",
  siteUrl: 'https://running.cigatang.space',
  logo: '/images/favicon.png',
  description: "Cigar's personal site and blog",
  navLinks: [
    {
      name: 'Home',
      url: 'https://cigatang.space',
    },
    {
      name: 'Photos',
      url: 'https://photos.cigatang.space',
    },
    {
      name: 'About',
      url: 'https://cigatang.space/about/',
    },
  ],
};

export default data;
