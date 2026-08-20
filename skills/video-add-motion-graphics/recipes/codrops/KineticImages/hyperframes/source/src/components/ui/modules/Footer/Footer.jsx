import styles from './Footer.module.scss';

function Footer({ children }) {
    return (
        <div className={styles.footer}>
            <div className={styles.wrapper}>{children}</div>
        </div>
    );
}

export default Footer;
