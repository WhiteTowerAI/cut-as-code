'use client';

import styles from './Loader.module.scss';

function Loader() {
    return (
        <div className={styles.loader}>
            <div className={styles.loader__text}>Loading...</div>
        </div>
    );
}

export default Loader;
